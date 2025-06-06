# 🎓 NovaFlow — Streamline Your Projects, Unleash Your Potential

![Cover](./assets/cover_image.png)

**NovaFlow** is a lightweight, web-based project management tool built with **Flask**. It helps individuals and small teams organize their projects and tasks efficiently with a clean, intuitive interface and powerful collaboration features.

---

## 🌐 Live Demo

👉 [**View Live Demo**](https://nova-flow-blush.vercel.app/)

---

## 🔥 Features

- 🔐 **User Authentication**: Secure sign-up and login/logout flow.
- 📁 **Project Management**: Create, update, track, and delete projects.
- ✅ **Task Management**: Assign, complete, and manage tasks with progress tracking.
- 👥 **Team Collaboration**: Create/join teams with unique IDs and manage team-based projects.
- 📝 **Markdown Support**: Write beautifully formatted descriptions using markdown.
- 📱 **Fully Responsive**: Built with Tailwind CSS for a mobile-friendly experience.
- ❌ **Custom 404 Page**: Friendly UX for broken or invalid routes.

---

## 📸 Project Screenshots

| Landing Page | Authentication | Dashboard  |
|----------|----------|--------|
| ![Screenshot 1](./assets/screenshot_1.png) | ![Screenshot 2](./assets/screenshot_2.png) | ![Screenshot 3](./assets/screenshot_3.png) |

---

## 🧠 How it Works

- Users register and join teams using unique Team IDs.
- Each project can be assigned a status: `Not Started`, `Planning`, `In Progress`, etc.
- Tasks belong to projects and reflect their team association.
- Descriptions use Markdown for rich formatting.
- A simple local database (JSON or SQLite) manages all data in development.

---

## 🛠️ Tech Stack

- **Backend**: Flask (Python)
- **Frontend**: Tailwind CSS, HTML, Jinja2
- **Auth & Logic**: Werkzeug, Markdown
- **Extras**: Font Awesome, Markdown-it

---

## 🚀 Getting Started



```bash
git clone https://github.com/khanfaisal79960/NovaFlow.git
cd NovaFlow
Download `firebase-adminsdk.json` from google firebase and put it in root directory
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt
python app.py
```

Now open your browser and visit: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

> 💡 Remove `_initialize_test_data()` from `app.py` before production deployment.

---

## 📁 Project Structure

```

NOVAFLOW/
├── assets/
│   ├── cover_image.png
│   ├── screenshot_1.png
│   ├── screenshot_2.png
│   └── screenshot_3.png
├── static/
│   ├── css/
│   │   └── style.css
│   ├── img/
│   │   ├── empty_state.gif
│   │   └── glitch_404.gif
│   ├── js/
│   │   └── theme.js
│   └── favicon.ico
├── templates/
│   ├── 404.html
│   ├── base.html
│   ├── create_project.html
│   ├── dashboard.html
│   ├── edit_project.html
│   ├── index.html
│   ├── login.html
│   ├── profile.html
│   ├── project_details.html
│   ├── register.html
│   └── tasks.html
├── app.py
├── firebase-adminsdk.json
├── README.md
├── requirements.txt

```

---

## 🙋‍♂️ Author

**Faisal Khan**

- 🌐 [Portfolio](https://khanfaisal.netlify.app)
- 💼 [LinkedIn](https://www.linkedin.com/in/khanfaisal79960)
- ✍️ [Medium](https://medium.com/@khanfaisal79960)
- 📸 [Instagram](https://instagram.com/mr._perfect_1004)
- 💻 [GitHub](https://github.com/khanfaisal79960)

---
