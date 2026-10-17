FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHON_VERSION=3.14
ENV NODE_MAJOR=24

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        gnupg \
        lsb-release \
        sudo \
        wget \
        build-essential \
        libcups2-dev \
        libffi-dev \
        libmariadb-dev \
        libssl-dev \
        mariadb-client \
        mariadb-server \
        redis-server \
        cron \
        software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Python 3.14 via deadsnakes
RUN add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        python3.14 \
        python3.14-dev \
        python3.14-venv \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.14 /usr/local/bin/python3 \
    && ln -sf /usr/bin/python3.14 /usr/local/bin/python

# Node.js 24
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && corepack enable \
    && corepack prepare yarn@1.22.22 --activate

# wkhtmltopdf for Frappe PDF features
RUN wget -q https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.jammy_amd64.deb \
    && apt-get update \
    && apt-get install -y ./wkhtmltox_0.12.6.1-3.jammy_amd64.deb \
    && rm -f wkhtmltox_0.12.6.1-3.jammy_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Bench CLI
RUN python3 -m pip install --no-cache-dir --break-system-packages frappe-bench

# Default MariaDB root password for local development only
RUN service mariadb start \
    && mariadb -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '123'; FLUSH PRIVILEGES;" \
    && service mariadb stop

# Allow passwordless sudo for service management in start.sh
RUN echo "ubuntu ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers.d/ubuntu \
    && chmod 0440 /etc/sudoers.d/ubuntu

USER ubuntu
WORKDIR /home/ubuntu
