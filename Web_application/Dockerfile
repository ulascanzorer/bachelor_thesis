FROM python:3

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install and start mongod, restore the database and start the server. After creation, we copy the database file into the container and then manually go in the container and restore the database and start the server.

CMD apt install gnupg curl && curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor && echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] http://repo.mongodb.org/apt/debian bookworm/mongodb-org/7.0 main" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list && apt update && apt install -y mongodb-org && apt install -y systemctl && systemctl start mongod && systemctl enable mongod && tail -f /dev/null
