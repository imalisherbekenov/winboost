# WinBoost PySide6 Migration Plan

## 1. Overview
Migrate the WinBoost system optimizer from CustomTkinter/Dear PyGui to a modern, robust PySide6-based application. The goal is to provide a "premium" desktop experience with a sidebar-based navigation, high-performance background tasks, and a polished dark-themed UI.

## 2. Technical Stack
- **Framework:** PySide6 (Qt for Python).
- **Theming:** `qt-material` (using 'dark_amber.xml' or 'dark_blue.xml' customized for WinBoost).
- **Threading:** `QThread` and `QSignaler` for non-blocking background tasks (scanning, applying fixes).
- **Icons:** Internal Qt resources or a light icon font integration.

## 3. UI/UX Architecture
### Main Window Structure
- **Left Sidebar:**
    - App Logo (WB.) and Title.
    - Navigation Buttons: Home, Wizard, Analysis, Expert, Startup, Backups, Log.
    - Theme Switcher (at the bottom).
- **Main Content (QStackedWidget):**
    - **Home Page:** Dash-style cards for quick actions.
    - **Wizard Page:** Step-by-step questionnaire using `QStackedWidget` for steps.
    - **Analysis Page:** Custom `CircularProgressBar` (QWidget) and detailed results table/tree.
    - **Expert Page:** Scrollable list of modules, each containing checkboxes for specific tweaks.
    - **Startup Page:** QTableWidget showing app name, location, and risk level with "Disable" buttons.
    - **Backups Page:** List of available registry/system backups with "Restore" buttons.
    - **Log Page:** Colored `QPlainTextEdit` for real-time logging.
- **Status Bar:**
    - App Version.
    - Admin Status (Colored label).
    - Background Task Status.
    - Digital Clock.

## 4. Implementation Details
### Background Processing
All heavy operations (registry edits, bloatware removal, system scanning) will run in background threads to keep the UI responsive.
- `ScanWorker(QThread)`: Handles system analysis.
- `ActionWorker(QThread)`: Handles applying optimization actions.
- Signals will update the UI on progress and completion.

### Custom Widgets
- **CircularProgressBar:** A custom QWidget using `QPainter` to draw the ring and percentage text.
- **ModernCard:** A styled QFrame with hover effects for the Home page.

## 5. Migration Steps
1. **Infrastructure:** Set up the main PySide6 application loop and window skeleton.
2. **Theming:** Integrate `qt-material` and define custom color overrides.
3. **Core Logic Wiring:** Adapt `modules/` calls to work with Qt Signals/Slots.
4. **Page Development:** Implement pages one by one, starting with Home and Log.
5. **Validation:** Ensure all optimization functions work correctly in the new environment and test admin elevation.

## 6. Dependencies to Add
- `PySide6`
- `qt-material`
- `psutil` (already in requirements)
