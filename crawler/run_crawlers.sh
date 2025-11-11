#!/bin/bash

# --- Configuration ---
# Define crawler directories and their corresponding commands in two separate arrays.
# Make sure the order of directories in CRAWLER_DIRS matches the order of commands in CRAWLER_CMDS.
CRAWLER_DIRS=(
    "adm/course-form"
    "adm/course-qa"
    "adm/courses"
    "adm/freshman"
    "adm/news"
    "adm/registration-form"
    "adm/registration-qa"
    "adm/regulations"
    "adm/statistics"
    "adm/tution"
    "csie/news"
)

CRAWLER_CMDS=(
    "python3 app.py"
    "python3 app.py"
    "python3 app.py"
    "python3 app.py"
    "python3 app.py"
    "python3 app.py"
    "python3 app.py"
    "python3 app.py"
    "python3 app.py"
    "python3 app.py"
    "python3 app.py"
)

# --- Virtual Environment Setup ---
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

# --- Dependency Installation ---
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt
echo "Dependencies installed."
echo

# --- Crawler Execution ---
declare -a results
for i in "${!CRAWLER_DIRS[@]}"; do
    crawler_dir="${CRAWLER_DIRS[$i]}"
    cmd="${CRAWLER_CMDS[$i]}"
    echo "----------------------------------------"
    echo "Running crawler in: $crawler_dir"
    echo "Command: $cmd"
    
    if [ -f "$crawler_dir/app.py" ]; then
        # Execute crawler and capture status
        (cd "$crawler_dir" && eval "$cmd")
        exit_code=$?
        
        if [ $exit_code -eq 0 ]; then
            echo "SUCCESS: Crawler '$crawler_dir' finished."
            results+=("SUCCESS: $crawler_dir")
        else
            echo "FAILURE: Crawler '$crawler_dir' failed with exit code $exit_code."
            results+=("FAILURE: $crawler_dir (Exit Code: $exit_code)")
        fi
    else
        echo "SKIPPED: 'app.py' not found in '$crawler_dir'."
        results+=("SKIPPED: $crawler_dir (app.py not found)")
    fi
    echo "----------------------------------------"
    echo
done

# --- Summary ---
echo "========================================"
echo "          CRAWLER RUN SUMMARY"
echo "========================================"
for result in "${results[@]}"; do
    echo "- $result"
done
echo "========================================"
