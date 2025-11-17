# How to Run the Crawler Docker Container

To run the crawler within a Docker container, follow these two steps:

1.  **Build the Docker image:**
    ```bash
    docker build -t ncu-campus-qa-bot-crawler .
    ```

2.  **Run the Docker container:**
    ```bash
    docker run --rm --shm-size=2g -v "$(pwd):/app" ncu-campus-qa-bot-crawler:latest
    ```

    *   `--rm`: Automatically remove the container when it exits.
    *   `--shm-size=2g`: Allocates 2GB of shared memory, which is often necessary for Chrome/Selenium to run stably in a Docker container.
    *   `-v "$(pwd):/app"`: Mounts your current working directory (where `run_crawlers.sh` and other crawler files are located) into the `/app` directory inside the container. This allows the container to access your scripts and save output files.
