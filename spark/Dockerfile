# Base image with Java pre-installed (Spark runs on the JVM)
FROM eclipse-temurin:17-jre-jammy

# Install Python and pip
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PySpark
RUN pip3 install --no-cache-dir pyspark==4.0.0

# Copy the job script and the data it processes
COPY spark_transaction_analysis.py .
COPY raw_transactions.csv .

CMD ["python3", "spark_transaction_analysis.py"]
