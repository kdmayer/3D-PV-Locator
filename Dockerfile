FROM python:3.8

# Install GDAL dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libgdal-dev

# Install Vim
RUN apt-get update && apt-get install -y vim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install the Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Set the entry point command for the container
CMD ["/bin/bash"]
