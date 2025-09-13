# GymGuardian 🏋️‍♂️🤖

**AI-powered workout form correction and feedback system**

## 📌 Problem Statement

Many people exercise without access to personal trainers, leading to poor form, increased risk of injury, and reduced efficiency. Existing AI-based solutions only classify reps as correct/incorrect without explaining _why_ or suggesting _how to improve_.

## 🎯 Goal

GymGuardian acts as a **virtual coach** that:

- Detects exercise reps using computer vision (MediaPipe + OpenCV).
- Identifies **joint-level errors** (e.g., knee collapsing, back rounding).
- Provides **highlighted replays** of faulty reps.
- Suggests **corrective micro-drills** for improvement.

## ✨ Key Features

- Real-time pose estimation using MediaPipe.
- Rep segmentation and per-rep error analysis.
- Joint-level blame localization.
- Replay of bad reps with visual highlights.
- Personalized corrective drill suggestions.
- Expandable for new exercises.

## 🏗️ Tech Stack

- **Language**: Python 3.x
- **Core Libraries**: MediaPipe, OpenCV, NumPy, scikit-learn (optional ML)
- **Architecture**: MVC (Models, Views, Controllers)
- **Deployment**: Flask or React (planned)
- **Version Control**: Git + GitHub

## 📂 Project Structure

GymGuardian/
├── src/
│ ├── models/ # AI + angle calculation logic
│ ├── views/ # UI layer
│ ├── controllers/ # connects input → models → output
│ ├── utils/ # helper scripts
│ └── init.py
├── models/ # saved ML models
├── data/ # sample videos/images
├── docs/ # reports, notes
├── tests/ # test scripts
├── requirements.txt # dependencies
├── .gitignore
└── README.md

## 🚀 Setup & Installation

To get a local copy up and running, follow these steps.

1.  **Clone the Repository**

    ```bash
    git clone [https://github.com/minababo/GymGuardian.git](https://github.com/minababo/GymGuardian.git)
    cd GymGuardian
    ```

2.  **Create and Activate a Virtual Environment**

    ```bash
    # Create the virtual environment
    python -m venv venv

    # Activate on Windows (Git Bash)
    source venv/Scripts/activate
    ```

3.  **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the Application** (Instructions to be added)
    ```bash
    python src/main.py
    ```
