FROM ruby:2.6-slim-buster

# Install dependencies for Oracle and other gems
RUN apt-get update && apt-get install -y \
    build-essential \
    nodejs \
    libaio1 \
    unzip \
    wget \
    git \
    libsqlite3-dev

# Install Oracle Instant Client
WORKDIR /opt/oracle
RUN wget https://download.oracle.com/otn_software/linux/instantclient/19600/instantclient-basic-linux.x64-19.6.0.0.0dbru.zip && \
    wget https://download.oracle.com/otn_software/linux/instantclient/19600/instantclient-sdk-linux.x64-19.6.0.0.0dbru.zip && \
    unzip instantclient-basic-linux.x64-19.6.0.0.0dbru.zip && \
    unzip instantclient-sdk-linux.x64-19.6.0.0.0dbru.zip && \
    rm -f *.zip

ENV LD_LIBRARY_PATH=/opt/oracle/instantclient_19_6:$LD_LIBRARY_PATH
ENV ORACLE_HOME=/opt/oracle/instantclient_19_6
ENV TNS_ADMIN=/opt/oracle/instantclient_19_6
ENV OCI_DIR=/opt/oracle/instantclient_19_6
ENV NLS_LANG=AMERICAN_AMERICA.AL32UTF8

# Set working directory
WORKDIR /app

# Install bundler version compatible with your app
RUN gem install bundler -v 1.17.3

# Install gems
COPY Gemfile Gemfile.lock ./
RUN bundle install

# Copy the rest of the application
COPY . .

# Command to run when container starts
CMD ["bundle", "exec", "rails", "server", "-b", "0.0.0.0"]