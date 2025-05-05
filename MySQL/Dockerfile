# Official MySQL image
FROM mysql:latest

# Default container configuration folder
ARG CONFIG_PATH="configuration"

# Copy init file for the database
COPY $CONFIG_PATH/employeesExampleDB.sql /docker-entrypoint-initdb.d/employeesExampleDB.sql

# Set the default user for the MySQL image
USER mysql

# Set environment variables for the new user
ENV MYSQL_USER=admin
ENV MYSQL_PASSWORD=password
ENV MYSQL_DATABASE=database

# Create the new user and grant them the necessary permissions
RUN mysql -u root -p -e "CREATE USER '$MYSQL_USER'@'%' IDENTIFIED BY '$MYSQL_PASSWORD';"
RUN mysql -u root -p -e "GRANT ALL PRIVILEGES ON $MYSQL_DATABASE.* TO '$MYSQL_USER'@'%';"
RUN mysql -u root -p -e "FLUSH PRIVILEGES;"

# Expose port 3306 to allow connections to the database
EXPOSE 3306

# Start the MySQL server when the container is run
CMD ["mysqld"]