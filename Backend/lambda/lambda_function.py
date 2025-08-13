import json
import boto3
import logging
from botocore.exceptions import ClientError
import os
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
qbusiness_client = boto3.client('qbusiness')

def lambda_handler(event, context):
    """
    AWS Lambda function for Catholic Charities Q Business chatbot
    - Stateless operation for simplicity
    - Anonymous access enabled
    - Returns simple response with sources
    """
    
    # Set response headers (CORS is handled by Lambda Function URL)
    headers = {
        'Content-Type': 'application/json'
    }
    
    try:
        # Get HTTP method from Lambda Function URL event format
        http_method = event.get('requestContext', {}).get('http', {}).get('method')
        
        # Handle preflight OPTIONS request
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'CORS preflight successful'})
            }
        
        # Handle health check (GET requests)
        if http_method == 'GET':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'status': 'healthy',
                    'service': 'Catholic Charities AI Assistant',
                    'timestamp': datetime.utcnow().isoformat()
                })
            }
        
        # Handle chat requests (POST requests)
        if http_method != 'POST':
            return {
                'statusCode': 405,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Method not allowed. Use POST for chat requests or GET for health checks.',
                    'success': False
                })
            }
        
        # Parse the request body
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        else:
            raise ValueError("Request body is missing")
        
        # Extract required parameters
        user_message = body.get('message', '').strip()
        
        if not user_message:
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps({
                    'error': 'Message is required',
                    'success': False
                })
            }
        
        # Get environment variables
        application_id = os.environ.get('QBUSINESS_APPLICATION_ID')
        
        if not application_id:
            raise ValueError("QBUSINESS_APPLICATION_ID environment variable is missing")
        
        # Call Q Business chat_sync API
        response = qbusiness_client.chat_sync(
            applicationId=application_id,
            userMessage=user_message
        )
        
        # Log the full API response for debugging
        logger.info(f"Q Business API Response: {response}")
        
        # Extract bot response from systemMessage
        bot_response = response.get('systemMessage', 'Sorry, I couldn’t find an answer.')
        
        # Extract and process source URLs with proper type detection
        sources = []
        if 'sourceAttributions' in response:
            for attribution in response['sourceAttributions']:
                if 'url' in attribution:
                    url = attribution.get("url")
                    title = attribution.get("title")
                    
                    # Determine if this is a document or web URL
                    is_document = (
                        url and (
                            '.s3.' in url or 
                            's3.amazonaws.com' in url or
                            url.endswith(('.pdf', '.docx', '.xlsx', '.doc', '.xls', '.txt'))
                        )
                    )
                    
                    sources.append({
                        "title": title,
                        "url": url,
                        "type": "DOCUMENT" if is_document else "WEB"
                    })

        # Prepare the response
        chat_response = {
            "success": True,
            "message": bot_response,
            "sources": sources,  # <-- now contains full objects
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "sourceCount": len(sources),
                "responseLength": len(bot_response),
                "applicationId": application_id
            }
        }

        logger.info(f"Prepared response with {len(sources)} sources")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(chat_response)
        }
        
    except ClientError as e:
        logger.error(f"AWS Client Error: {str(e)}")
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        # Handle specific Q Business errors
        if error_code == 'AccessDeniedException':
            error_message = "Access denied to Q Business application. Please check permissions."
        elif error_code == 'ResourceNotFoundException':
            error_message = "Q Business application not found. Please check the application ID."
        elif error_code == 'ThrottlingException':
            error_message = "Request was throttled. Please try again later."
        elif error_code == 'ValidationException':
            error_message = f"Validation error: {error_message}"
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': f"AWS Error ({error_code}): {error_message}",
                'success': False,
                'errorCode': error_code
            })
        }
        
    except ValueError as e:
        logger.error(f"Validation Error: {str(e)}")
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({
                'error': str(e),
                'success': False
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'success': False,
                'details': str(e) if os.environ.get('DEBUG') == 'true' else None
            })
        }