# Backend for Catholic Charities AI Assistant

## Overview

The backend of the Catholic Charities AI Assistant is responsible for managing data sources, processing user queries, and automating deployments. It leverages AWS services orchestrated through AWS CDK to provide a scalable and maintainable serverless infrastructure. This README provides a detailed explanation of the backend architecture, component interactions, deployment process, and configuration.

The backend uses **Lambda Function URLs** for direct HTTP access, providing simple configuration and cost-effective operation with built-in CORS support.

## Table of Contents

- [Architecture](#architecture)
  - [Key Components](#key-components)
  - [Lambda Functions](#lambda-functions)
- [Component Interactions](#component-interactions)
- [Deployment Process](#deployment-process)
- [Configuration](#configuration)
- [Monitoring and Logging](#monitoring-and-logging)
- [Adding New Data Sources](#adding-new-data-sources)
- [Important Notes](#important-notes)

## Architecture

The backend architecture is built using AWS services defined as code via AWS CDK. It consists of the following key components:

### Key Components

- **Amazon S3 Buckets**:
  - `DataSourceBucket`: Stores text files (e.g., `urls1.txt`) containing URLs to be crawled and document files (PDF, DOCX, XLSX, CSV) for indexing by Amazon Q Business.
  - `FrontendBuildBucket`: Stores zipped frontend build artifacts for automated deployment.

- **Amazon Q Business**:
  - An application with an index and retriever for conversational AI capabilities.
  - Multiple data sources are created: web crawlers for URL files and S3 document sources for uploaded files.

- **AWS Lambda Functions**:
  - Manage data sources, handle chat queries via Function URLs, and automate frontend deployments.

- **Lambda Function URLs**:
  - Provides direct HTTP endpoints for chat and health check functionality.
  - Offers simple configuration and cost-effective operation.
  - Includes built-in CORS support for cross-origin requests.

- **EventBridge**:
  - Monitors S3 uploads to the `FrontendBuildBucket` and triggers automated deployments.

### Lambda Functions

- **DataSourceCreator**:
  - **Runtime**: Python 3.11
  - **Handler**: `index.handler`
  - **Purpose**: Reads URL files and document files from the `DataSourceBucket` and creates corresponding data sources in Amazon Q Business (web crawlers for URLs, S3 sources for documents).
  - **Trigger**: Invoked as a custom resource during CDK stack deployment.
  - **Features**: Automatically starts sync jobs after data source creation.

- **ChatLambdaFunction**:
  - **Runtime**: Python 3.11
  - **Handler**: `lambda_function.lambda_handler`
  - **Purpose**: Handles incoming chat queries and health checks via Lambda Function URL, interacts with Amazon Q Business to get responses, and returns results with source attributions.
  - **Trigger**: Direct HTTP requests via Lambda Function URL (GET for health, POST for chat).
  - **Features**: Stateless operation, CORS support, enhanced error handling.

- **AmplifyDeployer**:
  - **Runtime**: Python 3.11
  - **Handler**: `index.handler`
  - **Purpose**: Starts AWS Amplify deployments when new frontend builds are uploaded to the `FrontendBuildBucket`.
  - **Trigger**: Invoked by EventBridge on S3 object creation events.
  - **Features**: Automatic deployment triggering via S3 upload events.

## Component Interactions

1. **Data Source Management**:
   - During stack deployment, the `DataSourceCreator` Lambda is invoked as a custom resource.
   - It reads `.txt` files (containing URLs) and document files (PDF, DOCX, XLSX, CSV) from the `DataSourceBucket`.
   - For each URL file, it creates a web crawler data source in Amazon Q Business.
   - For each document file, it creates an S3 data source with appropriate inclusion/exclusion patterns.
   - Automatically starts sync jobs for all created data sources.

2. **Chat Functionality**:
   - When a user submits a query via the frontend, it sends a POST request directly to the Lambda Function URL.
   - The `ChatLambdaFunction` receives the request with built-in CORS handling.
   - The Lambda function extracts the user's message and calls the Amazon Q Business `chat_sync` API.
   - Amazon Q Business processes the query using its indexed data and returns a response with source attributions.
   - The Lambda function formats the response with enhanced source attribution (web vs document sources) and returns it directly to the frontend.

3. **Health Check**:
   - GET requests to the Lambda Function URL return health status information.
   - Used for monitoring and verification of backend availability.

4. **Deployment Automation**:
   - When a new frontend build is ready, it's zipped and uploaded to the `FrontendBuildBucket` with a key starting with `builds/`.
   - EventBridge detects this upload and triggers the `AmplifyDeployer` Lambda.
   - The Lambda function retrieves the Amplify app ID and branch name from its environment variables.
   - It then calls the AWS Amplify API to start a deployment using the uploaded build artifact.
   - This ensures that the latest frontend is automatically deployed without manual intervention.

## Deployment Process

The backend is deployed using AWS CDK, with the deployment process automated through AWS CodeBuild.

- **deploy.sh**:
  - Prompts the user for necessary parameters (e.g., GitHub URL, project name, AWS region).
  - Creates or updates an IAM role for CodeBuild.
  - Sets up a CodeBuild project with the specified parameters.
  - Starts a build that executes the `buildspec.yml` file.

- **buildspec.yml**:
  - Installs dependencies and the AWS CDK CLI.
  - Bootstraps the CDK environment.
  - Deploys the CDK stack, which provisions all backend resources.
  - Tests the Lambda Function URL endpoints (health check).
  - Creates/updates Amplify application with environment variables.
  - Builds the frontend, uploads the build artifact to S3, and triggers the automated deployment via EventBridge.
  - Configures the AmplifyDeployer Lambda with Amplify app details.

This process ensures consistent deployment and configuration across different environments.

## Configuration

The backend relies on several parameters and environment variables:

- **Parameters** (provided via `deploy.sh` or CDK context):
  - `projectName`: Used to name resources uniquely.
  - `urlFilesPath`: Location of the URL files for data sources.
  - `amplifyAppName` and `amplifyBranchName`: For frontend deployment.
  - `AWS_REGION`: The region where resources are deployed (default: `us-west-2`).

- **Environment Variables**:
  - `QBUSINESS_APPLICATION_ID`: Set in the `ChatLambdaFunction` to identify the Amazon Q Business application.
  - `DEBUG`: Optional flag in `ChatLambdaFunction` for detailed error logging.
  - `AMPLIFY_APP_ID` and `AMPLIFY_BRANCH_NAME`: Set in the `AmplifyDeployer` Lambda for deployment automation.

These parameters are passed to the CDK stack and CodeBuild environment during deployment.

## Monitoring and Logging

- All Lambda functions are configured to log to AWS CloudWatch.
- Lambda Function URLs provide built-in metrics for request count, duration, and errors.
- Amazon Q Business provides its own logging and monitoring capabilities through CloudWatch.
- EventBridge rules can be monitored for deployment automation events.

It is recommended to set up CloudWatch alarms and dashboards for critical metrics, such as:
- Lambda function errors and duration
- Lambda Function URL response times
- Q Business query success rates
- Amplify deployment success/failure rates

## Adding New Data Sources

### Web URLs
To add new URLs for indexing:

1. Create a new `.txt` file in the `data-sources` directory, listing the URLs to be crawled (one per line).
2. Redeploy the stack to create a new web crawler data source for the additional URLs.

### Documents
To add document sources:

1. Place PDF, DOCX, XLSX, or CSV files directly in the `data-sources` directory.
2. Redeploy the stack to create S3 data sources for the documents.

### Manual Management
Alternatively, you can manually add data sources through the Amazon Q Business console after deployment.

### Limits
- Up to 50 data sources per Q Business application
- Up to 100 URLs per web crawler data source
- Document size limits apply per AWS Q Business quotas

## Important Notes

- **Lambda Function URLs**: The backend uses Lambda Function URLs for direct HTTP access, providing simple configuration and cost-effective operation.
- **Anonymous Access**: The Lambda Function URL is configured for anonymous access with CORS support for cross-origin requests.
- **Region Selection**: The project is optimized for the `us-west-2` region. Deployment in other regions may require additional configuration.
- **Data Source Syncing**: Sync jobs are automatically started after data source creation with a polling mechanism to ensure readiness.
- **URL Accessibility**: Ensure that all URLs in the data source files are publicly accessible and not restricted by geo-location or IP rules.
- **Document Support**: The backend automatically creates appropriate S3 data sources for PDF, DOCX, XLSX, and CSV files with proper inclusion/exclusion patterns.
- **Custom Resource for Data Sources**: The `DataSourcesCustomResource` is a CDK custom resource that invokes the `DataSourceCreator` Lambda during stack deployment, ensuring data sources are automatically created based on files in S3.
- **Stateless Operation**: The chat functionality operates statelessly for better scalability and reliability.

## File Structure

```
Backend/
├── bin/
│   └── catholic-charities-cdk.ts    # CDK app entry point
├── data-sources/                    # Data source files
│   ├── urls1.txt                   # URLs for web crawling
│   └── urls2.txt                   # Additional URLs for web crawling
│   └── *.pdf, *.docx, *.xlsx, *.csv # Document files for indexing
├── lambda/
│   └── lambda_function.py          # Chat handler with Function URL support
├── lib/
│   └── catholic-charities-stack.ts # CDK stack definition
├── buildspec.yml                   # CodeBuild configuration
├── deploy.sh                       # Deployment automation script
├── package.json                    # Node.js dependencies
└── README.md                       
```