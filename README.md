# GymGuardian

AI-powered exercise form analysis and feedback system using computer vision.

## Problem Statement

Many individuals perform exercises without access to professional coaching, leading to incorrect form, increased injury risk, and reduced training effectiveness. While AI-based fitness tools exist, many provide only basic rep counting or binary correctness feedback without meaningful insight into movement quality.

## Project Aim

GymGuardian aims to provide real-time exercise form analysis using pose estimation techniques. The system focuses on identifying posture states and movement patterns during exercises, enabling basic feedback and session-level analysis suitable for a prototype-level academic project.

## Key Features

- Real-time pose detection using MediaPipe and OpenCV
- Live webcam feed with skeletal overlay
- Exercise state classification (e.g., squat phases)
- Session recording and summary output
- Configurable thresholds for posture analysis
- Modular structure for extending to additional exercises

## Technology Stack

- **Language**: Python 3.x
- **Computer Vision**: MediaPipe, OpenCV
- **Numerical Processing**: NumPy
- **Architecture**: Modular Python application
- **Version Control**: Git and GitHub

## Project Structure

```
GymGuardian/
├── src/
│ ├── analysis/ # exercise state and form analysis
│ ├── pose/ # pose detection logic
│ ├── session/ # session recording and summaries
│ ├── ui/ # visual overlays and display
│ ├── core/ # configuration and shared utilities
│ └── app.py # application entry point
├── assets/
│ └── models/ # pose models (ignored from version control)
├── requirements.txt
├── .gitignore
└── README.md
```

## Setup & Installation

### Prerequisites

- Python 3.9 or later
- Webcam

### Installation Steps

1.  **Clone the Repository**

    ```bash
    git clone https://github.com/minababo/GymGuardian.git
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

4.  **Run the Application**
    ```bash
    python src/app.py
    ```

Press q or Esc to exit the application window.

## Project Status

This project is developed as part of the PUSL3190 Computing Project module and represents a prototype-level implementation aligned with academic assessment requirements.

## License

This project is intended for academic use.
