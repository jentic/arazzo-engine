# Docker and AWS ECS Deployment Guide

This guide explains how to use Docker with the Jentic Arazzo Generator and deploy it to AWS ECS.

## Docker Setup

The project includes Docker configurations for both the API server and CLI tool modes:

- `docker/Dockerfile`: Multi-purpose container that can run either the API server or CLI tool
- `docker/docker-compose.yml`: Local development setup with services for both API and CLI
- `docker/.dockerignore`: Optimizes Docker builds by excluding unnecessary files
- `docker/.env`: Environment variables file for storing API keys and configuration
- `docker/.env.example`: Template for the environment variables file

## Local Docker Usage

### Environment Setup

The Docker configuration uses environment variables for API keys and other settings:

1. We provide a template file `.env.example` that shows the structure and expected variables
2. You should create your own `.env` file with your actual API keys:

```bash
cp docker/.env.example docker/.env
# Edit docker/.env with your actual API keys
```

3. The `.env` file is included in `.gitignore` to prevent committing sensitive information

The `.env` file supports the following variables:
   - `ANTHROPIC_API_KEY`: API key for Anthropic Claude
   - `OPENAI_API_KEY`: API key for OpenAI ChatGPT
   - `GEMINI_API_KEY`: API key for Google Gemini
   - `HOST`: Host address for the API server (default: 0.0.0.0)
   - `PORT`: Port for the API server (default: 8000)
   - `LOG_LEVEL`: Logging level (default: info)

### Building the Docker Image

```bash
# From the project root directory
docker build --platform linux/amd64 -t jentic-arazzo-generator -f docker/Dockerfile .
```

### Running the API Server

```bash
# Using docker directly with .env file
docker run -p 8000:8000 \
  --env-file docker/.env \
  jentic-arazzo-generator

# Using docker-compose (from the project root)
docker-compose -f docker/docker-compose.yml up arazzo-api
```

### Running the CLI Tool

```bash
# Using docker directly with .env file
docker run --rm \
  --env-file docker/.env \
  -v $(pwd)/output:/app/output \
  jentic-arazzo-generator python -m generator.arazzo_generator.cli.main generate <url> --output /app/output/result.yaml

# Using docker-compose (from the project root)
docker-compose -f docker/docker-compose.yml run arazzo-cli generate <url> --output /app/output/result.yaml
```

## AWS ECS Deployment (EC2 / Bridge Mode)

These steps outline deploying the Arazzo Generator as an API service on AWS ECS using the EC2 launch type and Bridge networking mode.

### Prerequisites

*   AWS CLI installed and configured (`aws configure`).
*   Docker installed.
*   An existing ECS Cluster (e.g., `ecs-qa1`) configured to use EC2 instances.
*   An existing Application Load Balancer (ALB) and a Target Group configured with `target-type: instance`.
*   SSM Parameters created for API keys (e.g., `/jentic/arazzo/gemini_api_key`, `/jentic/arazzo/anthropic_api_key`, `/jentic/arazzo/openai_api_key`).

### 1. Create IAM Task Execution Role

An IAM role is required for ECS tasks to pull images from ECR and read secrets from SSM.

Create `trust-policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Create the role and attach required policies:
```bash
# Replace <your-region> and <your-account-id> with your specific values
AWS_REGION=<your-region>
ROLE_NAME=ecsTaskExecutionRole

aws iam create-role --role-name ${ROLE_NAME} --assume-role-policy-document file://trust-policy.json --region ${AWS_REGION}

# Attach standard ECS Task Execution policy
aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy --region ${AWS_REGION}

# Attach policy for SSM Parameter Store access (adjust if using different secret storage)
aws iam attach-role-policy --role-name ${ROLE_NAME} --policy-arn arn:aws:iam::aws:policy/AmazonSSMReadOnlyAccess --region ${AWS_REGION}
```

*Note: Ensure the user/role performing the deployment has `iam:PassRole` permissions for this execution role.*

### 2. Build and Push Docker Image

```bash
# Replace <your-account-id>, <your-region>, and <repo-name> (e.g., jentic-arazzo-generator)
AWS_ACCOUNT_ID=<your-account-id>
AWS_REGION=<your-region>
ECR_REPO_NAME=<repo-name>
IMAGE_TAG=latest

# Build for linux/amd64 architecture
docker build --platform linux/amd64 -t ${ECR_REPO_NAME}:${IMAGE_TAG} -f docker/Dockerfile ..

# Login to ECR
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Tag the image
docker tag ${ECR_REPO_NAME}:${IMAGE_TAG} ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}

# Push the image
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}:${IMAGE_TAG}
```

### 3. Configure Task Definition

The `docker/ecs-task-def.json` file defines the task. Key configurations for EC2/Bridge mode:

*   `family`: A unique name (e.g., `jentic-arazzo-generator-task`).
*   `networkMode`: Set to `bridge`.
*   `executionRoleArn`: The ARN of the `ecsTaskExecutionRole` created in Step 1.
*   `containerDefinitions[].portMappings`: Define `containerPort` (e.g., 8000) and set `hostPort` to `0` for dynamic port allocation.
*   `containerDefinitions[].secrets`: Configure `valueFrom` to point to your SSM Parameter ARNs for API keys.
*   `containerDefinitions[].logConfiguration`: Define `awslogs-group` (e.g., `/ecs/jentic-arazzo-generator-task`), `awslogs-region`, and `awslogs-stream-prefix`.
*   `cpu` and `memory`: Define resource limits (these are reservations for EC2, not hard limits like Fargate).
*   Remove `requiresCompatibilities` or set it to `["EC2"]`.

**Update `docker/ecs-task-def.json` with your specific ARNs, region, account ID, log group name, and repository URI.**

### 4. Create CloudWatch Log Group

The log group specified in the task definition must exist before tasks can start.

```bash
# Replace <log-group-name> (e.g., /ecs/jentic-arazzo-generator-task) and <your-region>
aws logs create-log-group --log-group-name <log-group-name> --region <your-region>
```

### 5. Register Task Definition

```bash
# Ensure you are in the docker/ directory or provide the full path
aws ecs register-task-definition --cli-input-json file://ecs-task-def.json --region <your-region>
```

Note the `taskDefinitionArn` from the output (e.g., `arn:aws:ecs:...:task-definition/your-family:1`).

### 6. Create or Update ECS Service

**If creating a new service:**

```bash
# Replace placeholders: <your-cluster>, <your-service-name>, <task-definition-arn:version>, <target-group-arn>, <container-name>, <container-port>
aws ecs create-service \
  --cluster <your-cluster> \
  --service-name <your-service-name> \
  --task-definition <task-definition-arn:version> \
  --desired-count 1 \
  --launch-type EC2 \
  --load-balancers targetGroupArn=<target-group-arn>,containerName=<container-name>,containerPort=<container-port> \
  --region <your-region>
```

**If updating an existing service (e.g., to deploy a new image version):**

```bash
# Replace placeholders: <your-cluster>, <your-service-name>, <task-definition-arn:version>
aws ecs update-service \
  --cluster <your-cluster> \
  --service <your-service-name> \
  --task-definition <task-definition-arn:version> \
  --force-new-deployment \
  --region <your-region>
```

### 7. Verify Deployment

*   Check the service status in the AWS ECS console or via CLI:
    ```bash
    aws ecs describe-services --cluster <your-cluster> --services <your-service-name> --region <your-region>
    ```
*   Check the target group health in the AWS EC2 console (Load Balancing -> Target Groups) or via CLI:
    ```bash
    aws elbv2 describe-target-health --target-group-arn <target-group-arn> --region <your-region>
    ```
*   Check container logs in CloudWatch Logs.
*   Access the service via the Load Balancer's DNS name.

## Environment Variables

The Docker setup supports the following environment variables:

- `ANTHROPIC_API_KEY`: API key for Anthropic Claude
- `OPENAI_API_KEY`: API key for OpenAI ChatGPT
- `GEMINI_API_KEY`: API key for Google Gemini
- `PYTHONPATH`: Set to `/app` in the container
- `PYTHONUNBUFFERED`: Set to `1` for unbuffered output

## Security Considerations

- Store API keys in AWS Secrets Manager or Parameter Store
- Use IAM roles with least privilege
- Configure security groups to restrict access to the service
- Consider using AWS WAF for additional protection

## Scaling

For production workloads, consider:

1. Setting up auto-scaling based on CPU/memory utilization
2. Using Application Load Balancer for distributing traffic
3. Implementing CloudWatch alarms for monitoring
4. Setting up proper logging and metrics collection
