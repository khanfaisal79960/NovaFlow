import os
from flask import Flask, render_template, redirect, url_for, request, session, flash, g
from firebase_admin import credentials, initialize_app, auth, firestore, exceptions
from dotenv import load_dotenv
from functools import wraps
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize Firebase Admin SDK
try:
    # This is the desired setup for using the file path
    service_account_key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")

    if not service_account_key_path:
        raise ValueError("FIREBASE_SERVICE_ACCOUNT_KEY environment variable not set.")

    # In a Vercel environment, this path will be relative to the deployment root.
    # Locally, it could be relative or absolute.
    # os.path.abspath will resolve it correctly in both contexts.
    absolute_key_path = os.path.abspath(service_account_key_path)

    if not os.path.exists(absolute_key_path):
        raise FileNotFoundError(f"Service account key file not found at: {absolute_key_path}")

    cred = credentials.Certificate(absolute_key_path)
    initialize_app(cred)
    db = firestore.client()
    print("Firebase initialized successfully.")
except Exception as e:
    print(f"Error initializing Firebase: {e}")
    # Consider handling this error more robustly, e.g., exiting or showing an error page

# Decorator to ensure user is logged in
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Before each request, set theme and user info in Flask's global 'g' object
@app.before_request
def set_theme_and_user():
    if 'theme' not in session:
        session['theme'] = 'light' # Default theme

    g.user = None # Firebase user object
    g.user_info = None # Dictionary of user details for templates

    if 'user_id' in session:
        try:
            user = auth.get_user(session['user_id'])
            g.user = user
            g.user_info = {
                'uid': user.uid,
                'email': user.email,
                'display_name': user.display_name if user.display_name else user.email, # Use email if display_name is not set
                'photo_url': user.photo_url # If you store profile photos
            }
        except Exception as e:
            print(f"Error fetching user data: {e}")
            session.pop('user_id', None) # Clear invalid session
            flash('Your session has expired. Please log in again.', 'warning')
            g.user_info = None # Ensure user_info is cleared on error

# Main routes
@app.route('/')
def index():
    return render_template('index.html', theme=session['theme'], user=g.user_info)

@app.route('/toggle_theme')
def toggle_theme():
    session['theme'] = 'dark' if session['theme'] == 'light' else 'light'
    return redirect(request.referrer or url_for('index')) # Redirect back to the page user came from

# Custom error handler for 404 Not Found
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', theme=session['theme'], user=g.user_info), 404

# --- User Authentication Routes ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if g.user: # If already logged in, redirect to dashboard
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            user = auth.create_user(email=email, password=password)
            session['user_id'] = user.uid # Log in the user automatically after registration
            flash('Registration successful! You are now logged in.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            error_message = str(e)
            if 'email-already-exists' in error_message:
                flash('Email already registered. Please try logging in.', 'danger')
            elif 'weak-password' in error_message:
                flash('Password is too weak. Must be at least 6 characters.', 'danger')
            else:
                flash(f'Registration failed: {error_message}', 'danger')
    return render_template('register.html', theme=session['theme'], user=g.user_info)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user: # If already logged in, redirect to dashboard
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        try:
            # Authenticate user with Firebase Authentication (client-side usually handles this)
            # For server-side, you'd typically use ID tokens from client, but for simplicity here,
            # we just check if user exists. This does NOT securely log in the user,
            # it just verifies their existence. A real app would exchange password for ID token.
            user = auth.get_user_by_email(email)
            # In a real app, you'd verify the password via client-side SDK or a custom auth token mechanism.
            # For this simple example, we're assuming if the email exists, we "log them in"
            # on the server by setting session['user_id'].
            session['user_id'] = user.uid
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        except auth.AuthError as e:
            flash('Invalid email or password.', 'danger')
        except Exception as e:
            flash(f'An unexpected error occurred: {str(e)}', 'danger')
    return render_template('login.html', theme=session['theme'], user=g.user_info)

@app.route('/logout')
@login_required
def logout():
    session.pop('user_id', None) # Remove user from session
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# --- Project Management Routes ---
@app.route('/dashboard')
@login_required
def dashboard():
    user_uid = g.user_info['uid']
    projects_ref = db.collection('projects')

    # Fetch projects where the current user is either the owner OR a collaborator
    # This involves two separate queries and merging the results, then eliminating duplicates.
    # Firestore doesn't directly support OR queries across different fields or array_contains + equality in a single query.

    owner_projects_query = projects_ref.where('owner_uid', '==', user_uid).stream()
    collaborator_projects_query = projects_ref.where('collaborators_uids', 'array_contains', user_uid).stream()

    all_project_ids = set()
    projects_dict = {} # Use a dict to store projects by ID to avoid duplicates and allow easy lookup

    for doc in owner_projects_query:
        project_data = doc.to_dict()
        project_data['id'] = doc.id
        projects_dict[doc.id] = project_data
        all_project_ids.add(doc.id)

    for doc in collaborator_projects_query:
        # Only add if not already added by owner_projects_query
        if doc.id not in all_project_ids:
            project_data = doc.to_dict()
            project_data['id'] = doc.id
            projects_dict[doc.id] = project_data
            all_project_ids.add(doc.id)

    # Convert the dictionary values back to a list and sort them
    projects = list(projects_dict.values())

    # Sort projects by created_at in descending order (most recent first)
    # Ensure 'created_at' exists and is a datetime object or equivalent
    projects.sort(key=lambda x: x.get('created_at', datetime.min), reverse=True)


    return render_template('dashboard.html', theme=session['theme'], user=g.user_info, projects=projects)

@app.route('/projects/create', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        project_name = request.form['name']
        project_description = request.form.get('description', '') # Optional description

        if not project_name:
            flash('Project name cannot be empty.', 'danger')
            return redirect(url_for('create_project'))

        try:
            new_project_ref = db.collection('projects').document() # Create a new document reference with auto-generated ID
            new_project_ref.set({
                'name': project_name,
                'description': project_description,
                'owner_uid': g.user_info['uid'], # Store the UID of the project owner
                'collaborators_uids': [], # NEW: Initialize as an empty list
                'created_at': firestore.SERVER_TIMESTAMP # Use Firestore's server timestamp
            })
            flash(f'Project "{project_name}" created successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error creating project: {str(e)}', 'danger')
            print(f"Error creating project: {e}") # Log the full error for debugging

    return render_template('create_project.html', theme=session['theme'], user=g.user_info)

@app.route('/projects/<project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    """Displays edit form for a project and handles its submission."""
    project_ref = db.collection('projects').document(project_id)
    project_doc = project_ref.get()

    if not project_doc.exists:
        flash('Project not found.', 'danger')
        return redirect(url_for('dashboard'))

    project = project_doc.to_dict()
    project['id'] = project_doc.id

    # Security Check: Ensure current user owns this project
    if project['owner_uid'] != g.user_info['uid']:
        flash('You do not have permission to edit this project.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        new_name = request.form['name']
        new_description = request.form.get('description', '')

        if not new_name:
            flash('Project name cannot be empty.', 'danger')
            return redirect(url_for('edit_project', project_id=project_id))

        try:
            project_ref.update({
                'name': new_name,
                'description': new_description
            })
            flash(f'Project "{new_name}" updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error updating project: {str(e)}', 'danger')
            print(f"Error updating project: {e}")

    # For GET request, render the form with existing project data
    return render_template('edit_project.html',
                           theme=session['theme'],
                           user=g.user_info,
                           project=project)

# NEW: Route for Deleting Projects
@app.route('/projects/<project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """Handles deleting a specific project and its tasks."""
    project_ref = db.collection('projects').document(project_id)
    project_doc = project_ref.get()

    if not project_doc.exists:
        flash('Project not found.', 'danger')
        return redirect(url_for('dashboard'))

    project_data = project_doc.to_dict()

    # Security Check: Only the project owner can delete
    if project_data['owner_uid'] != g.user_info['uid']:
        flash('You do not have permission to delete this project.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        project_name = project_data.get('name', 'Unknown Project')

        # --- IMPORTANT: Delete all tasks (subcollection) first ---
        # Firestore doesn't automatically delete subcollections when parent document is deleted.
        # You must explicitly delete all documents in the 'tasks' subcollection.
        tasks_ref = project_ref.collection('tasks')
        tasks = tasks_ref.stream() # Get all task documents

        for task_doc in tasks:
            task_doc.reference.delete() # Delete each task document

        # --- Now delete the project document itself ---
        project_ref.delete()
        flash(f'Project "{project_name}" and all its tasks deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting project: {str(e)}', 'danger')
        print(f"Error deleting project: {e}") # Log the full error for debugging
        
    return redirect(url_for('dashboard'))

# NEW: Route for Inviting Collaborators
@app.route('/projects/<project_id>/invite_collaborator', methods=['POST'])
@login_required
def invite_collaborator(project_id):
    """Handles inviting a collaborator to a project."""
    invited_email = request.form.get('email', '').strip()

    if not invited_email:
        flash('Email address cannot be empty.', 'danger')
        return redirect(url_for('project_details', project_id=project_id))

    project_ref = db.collection('projects').document(project_id)
    project_doc = project_ref.get()

    if not project_doc.exists:
        flash('Project not found.', 'danger')
        return redirect(url_for('dashboard'))

    project_data = project_doc.to_dict()

    # Security Check: Only the project owner can invite
    if project_data['owner_uid'] != g.user_info['uid']:
        flash('You do not have permission to invite collaborators to this project.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        # Get the UID of the invited user by their email
        invited_user = auth.get_user_by_email(invited_email)
        invited_uid = invited_user.uid

        # Prevent inviting self
        if invited_uid == g.user_info['uid']:
            flash('You cannot invite yourself to collaborate.', 'warning')
            return redirect(url_for('project_details', project_id=project_id))

        # Prevent adding an already existing collaborator
        if invited_uid in project_data.get('collaborators_uids', []):
            flash(f'{invited_email} is already a collaborator on this project.', 'info')
            return redirect(url_for('project_details', project_id=project_id))

        # Add the invited user's UID to the collaborators_uids array
        project_ref.update({
            'collaborators_uids': firestore.ArrayUnion([invited_uid])
        })
        flash(f'Successfully invited {invited_email} to collaborate!', 'success')

    except auth.UserNotFoundError: # Correct exception for user not found by email
        flash(f'No user found with email: {invited_email}. Please ensure they have registered an account.', 'danger')
    except exceptions.FirebaseError as e: # Catch other general Firebase errors
        flash(f'A Firebase error occurred: {str(e)}', 'danger')
        print(f"Firebase error inviting collaborator: {e}")
    except Exception as e: # Catch any other unexpected errors
        flash(f'An unexpected error occurred: {str(e)}', 'danger')
        print(f"Unexpected error inviting collaborator: {e}")

    return redirect(url_for('project_details', project_id=project_id))


# --- Task Management Routes ---
@app.route('/projects/<project_id>')
@login_required
def project_details(project_id):
    """Displays details of a single project and its tasks."""
    project_ref = db.collection('projects').document(project_id)
    project_doc = project_ref.get()

    if not project_doc.exists:
        flash('Project not found.', 'danger')
        return redirect(url_for('dashboard'))

    project = project_doc.to_dict()
    project['id'] = project_doc.id # Add ID to the project dictionary

    # Security Check: Ensure current user owns this project or is a collaborator
    is_owner = project['owner_uid'] == g.user_info['uid']
    is_collaborator = g.user_info['uid'] in project.get('collaborators_uids', [])

    if not (is_owner or is_collaborator):
        flash('You do not have permission to view this project.', 'danger')
        return redirect(url_for('dashboard'))

    # Fetch tasks for this project
    tasks_ref = project_ref.collection('tasks')
    project_tasks = tasks_ref.order_by('created_at', direction=firestore.Query.ASCENDING).stream()

    tasks = []
    for doc in project_tasks:
        task_data = doc.to_dict()
        task_data['id'] = doc.id # Add document ID to each task dictionary
        tasks.append(task_data)

    # NEW: Fetch collaborator details (UID and Email)
    collaborators_info = []
    # Ensure project.get('collaborators_uids', []) provides a list to iterate
    for c_uid in project.get('collaborators_uids', []):
        try:
            collaborator_user = auth.get_user(c_uid)
            collaborators_info.append({
                'uid': c_uid,
                'email': collaborator_user.email,
                'display_name': collaborator_user.display_name # Optionally get display name too
            })
        except auth.UserNotFoundError:
            # Handle case where a UID in the list no longer corresponds to an active user
            print(f"Collaborator UID {c_uid} not found in Firebase Auth.")
            collaborators_info.append({'uid': c_uid, 'email': 'Unknown User (Deleted)', 'display_name': 'Unknown'})
        except Exception as e:
            print(f"Error fetching collaborator {c_uid} info: {e}")
            collaborators_info.append({'uid': c_uid, 'email': 'Error Fetching Email', 'display_name': 'Error'})

    # Update the return statement to pass this new data
    return render_template('project_details.html',
                           theme=session['theme'],
                           user=g.user_info,
                           project=project,
                           tasks=tasks,
                           collaborators_info=collaborators_info)

@app.route('/projects/<project_id>/add_task', methods=['POST'])
@login_required
def add_task(project_id):
    """Handles adding a new task to a specific project."""
    task_title = request.form['title']
    task_description = request.form.get('description', '')
    
    if not task_title:
        flash('Task title cannot be empty.', 'danger')
        return redirect(url_for('project_details', project_id=project_id))

    project_ref = db.collection('projects').document(project_id)
    project_doc = project_ref.get()

    if not project_doc.exists:
        flash('Project not found.', 'danger')
        return redirect(url_for('dashboard'))

    project_data = project_doc.to_dict()
    # Ensure current user owns project or is a collaborator to add tasks
    is_owner = project_data['owner_uid'] == g.user_info['uid']
    is_collaborator = g.user_info['uid'] in project_data.get('collaborators_uids', [])

    if not (is_owner or is_collaborator):
        flash('You do not have permission to add tasks to this project.', 'danger')
        return redirect(url_for('dashboard'))

    try:
        tasks_ref = project_ref.collection('tasks')
        new_task_ref = tasks_ref.document()
        new_task_ref.set({
            'title': task_title,
            'description': task_description,
            'status': 'pending', # Default status for new tasks
            'created_at': firestore.SERVER_TIMESTAMP
        })
        flash(f'Task "{task_title}" added successfully!', 'success')
    except Exception as e:
        flash(f'Error adding task: {str(e)}', 'danger')
        print(f"Error adding task: {e}")
        
    return redirect(url_for('project_details', project_id=project_id))

@app.route('/projects/<project_id>/tasks/<task_id>/toggle_status', methods=['POST'])
@login_required
def toggle_task_status(project_id, task_id):
    """Toggles the status of a specific task."""
    project_ref = db.collection('projects').document(project_id)
    project_doc = project_ref.get()

    if not project_doc.exists:
        flash('Project not found.', 'danger')
        return redirect(url_for('dashboard'))

    project_data = project_doc.to_dict()
    # Ensure current user owns project or is a collaborator to modify tasks
    is_owner = project_data['owner_uid'] == g.user_info['uid']
    is_collaborator = g.user_info['uid'] in project_data.get('collaborators_uids', [])

    if not (is_owner or is_collaborator):
        flash('You do not have permission to modify tasks in this project.', 'danger')
        return redirect(url_for('dashboard'))

    task_ref = project_ref.collection('tasks').document(task_id)
    task_doc = task_ref.get()

    if not task_doc.exists:
        flash('Task not found.', 'danger')
        return redirect(url_for('project_details', project_id=project_id))

    current_status = task_doc.to_dict().get('status', 'pending')
    new_status = 'completed' if current_status == 'pending' else 'pending'

    try:
        task_ref.update({'status': new_status})
        flash(f'Task "{task_doc.to_dict().get("title", "Unknown Task")}" marked as {new_status}.', 'success')
    except Exception as e:
        flash(f'Error updating task status: {str(e)}', 'danger')
        print(f"Error updating task status: {e}")
        
    return redirect(url_for('project_details', project_id=project_id))

@app.route('/projects/<project_id>/tasks/<task_id>/edit', methods=['POST'])
@login_required
def edit_task(project_id, task_id):
    """Handles updating the details of a specific task."""
    project_ref = db.collection('projects').document(project_id)
    project_doc = project_ref.get()

    if not project_doc.exists:
        flash('Project not found.', 'danger')
        return redirect(url_for('dashboard'))

    project_data = project_doc.to_dict()
    # Ensure current user owns project or is a collaborator to modify tasks
    is_owner = project_data['owner_uid'] == g.user_info['uid']
    is_collaborator = g.user_info['uid'] in project_data.get('collaborators_uids', [])

    if not (is_owner or is_collaborator):
        flash('You do not have permission to modify tasks in this project.', 'danger')
        return redirect(url_for('dashboard'))

    task_ref = project_ref.collection('tasks').document(task_id)
    task_doc = task_ref.get()

    if not task_doc.exists:
        flash('Task not found.', 'danger')
        return redirect(url_for('project_details', project_id=project_id))

    new_title = request.form['title']
    new_description = request.form.get('description', '')

    if not new_title:
        flash('Task title cannot be empty.', 'danger')
        return redirect(url_for('project_details', project_id=project_id))

    try:
        task_ref.update({
            'title': new_title,
            'description': new_description
        })
        flash(f'Task "{new_title}" updated successfully!', 'success')
    except Exception as e:
        flash(f'Error updating task: {str(e)}', 'danger')
        print(f"Error updating task: {e}")
        
    return redirect(url_for('project_details', project_id=project_id))

@app.route('/projects/<project_id>/tasks/<task_id>/delete', methods=['POST'])
@login_required
def delete_task(project_id, task_id):
    """Handles deleting a specific task."""
    project_ref = db.collection('projects').document(project_id)
    project_doc = project_ref.get()

    if not project_doc.exists:
        flash('Project not found.', 'danger')
        return redirect(url_for('dashboard'))

    project_data = project_doc.to_dict()
    # Ensure current user owns project or is a collaborator to delete tasks
    is_owner = project_data['owner_uid'] == g.user_info['uid']
    is_collaborator = g.user_info['uid'] in project_data.get('collaborators_uids', [])

    if not (is_owner or is_collaborator):
        flash('You do not have permission to delete tasks in this project.', 'danger')
        return redirect(url_for('dashboard'))

    task_ref = project_ref.collection('tasks').document(task_id)
    task_doc = task_ref.get()

    if not task_doc.exists:
        flash('Task not found.', 'danger')
        return redirect(url_for('project_details', project_id=project_id))

    try:
        task_title = task_doc.to_dict().get('title', 'Unknown Task') # Get title before deleting
        task_ref.delete()
        flash(f'Task "{task_title}" deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting task: {str(e)}', 'danger')
        print(f"Error deleting task: {e}")
        
    return redirect(url_for('project_details', project_id=project_id))

# NEW: User Profile Route
@app.route('/profile')
@login_required
def profile():
    """Displays the user's profile information and settings."""
    return render_template('profile.html', theme=session['theme'], user=g.user_info)

# Placeholder route for general tasks view (can be enhanced later)
@app.route('/tasks') 
@login_required
def tasks():
    """Renders the general tasks page (requires login)."""
    # This route could eventually list all tasks across all projects for a user,
    # or redirect to dashboard/specific project if no global tasks view is desired.
    return render_template('tasks.html', theme=session['theme'], user=g.user_info)


if __name__ == '__main__':
    app.run(debug=True)