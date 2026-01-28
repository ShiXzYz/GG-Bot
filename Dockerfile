# Use Python slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy all bot files into container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "bot.py"]
