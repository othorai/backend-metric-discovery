#!/bin/bash

set -e  # Exit on error

# Load environment variables
source deployment/scripts/load-env.sh
load_env

# Constants
MAX_LENGTH=28
TRIMMED_METRIC_DISCOVERY_APP_NAME="${METRIC_DISCOVERY_APP_NAME:0:$MAX_LENGTH}"
VPC_ID="vpc-06739f6c62b9b0da7"
METRIC_DISCOVERY_ALB_ARN="arn:aws:elasticloadbalancing:eu-north-1:533267025675:loadbalancer/app/backend-chatbot-alb/14d33b15f13e7336"
METRIC_DISCOVERY_LISTENER_ARN="arn:aws:elasticloadbalancing:eu-north-1:533267025675:listener/app/backend-chatbot-alb/14d33b15f13e7336/c57f6cce1504a047"

echo "Creating new target group in chatbot VPC..."
NEW_TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
    --name "${TRIMMED_METRIC_DISCOVERY_APP_NAME}-tg-new" \
    --protocol HTTP \
    --port 8000 \
    --vpc-id ${VPC_ID} \
    --target-type ip \
    --health-check-path "/docs" \
    --health-check-interval-seconds 30 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --health-check-timeout-seconds 5 \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

echo "New target group created: ${NEW_TARGET_GROUP_ARN}"

# Create/Update listener rule to associate target group with ALB
echo "Creating listener rule..."
HIGHEST_PRIORITY=$(aws elbv2 describe-rules \
    --listener-arn "${METRIC_DISCOVERY_LISTENER_ARN}" \
    --query 'max_by(Rules, &Priority).Priority' \
    --output text \
    2>/dev/null || echo "0")

if [ "$HIGHEST_PRIORITY" = "None" ] || [ "$HIGHEST_PRIORITY" = "0" ]; then
    NEW_PRIORITY=1
else
    NEW_PRIORITY=$((HIGHEST_PRIORITY + 1))
fi

aws elbv2 create-rule \
    --listener-arn "${METRIC_DISCOVERY_LISTENER_ARN}" \
    --priority ${NEW_PRIORITY} \
    --conditions "[{\"Field\":\"path-pattern\",\"Values\":[\"/${METRIC_DISCOVERY_APP_NAME}/*\"]}]" \
    --actions "[{\"Type\":\"forward\",\"TargetGroupArn\":\"${NEW_TARGET_GROUP_ARN}\"}]" \
    --output text \
    --query 'Rules[0].RuleArn'

echo "Updating ECS service..."
aws ecs update-service \
    --cluster "${METRIC_DISCOVERY_CLUSTER_NAME}" \
    --service "${METRIC_DISCOVERY_SERVICE_NAME}" \
    --task-definition "${METRIC_DISCOVERY_APP_NAME}" \
    --force-new-deployment \
    --network-configuration "{\"awsvpcConfiguration\":{\"subnets\":[\"${VPC_SUBNET_1}\",\"${VPC_SUBNET_2}\"],\"securityGroups\":[\"${SECURITY_GROUP}\"],\"assignPublicIp\":\"ENABLED\"}}" \
    --load-balancers "[{\"targetGroupArn\":\"${NEW_TARGET_GROUP_ARN}\",\"containerName\":\"${METRIC_DISCOVERY_APP_NAME}\",\"containerPort\":8000}]" \
    --health-check-grace-period-seconds 120

# Update .env file with new ARNs
echo "Updating .env file with new ARNs..."
sed -i.bak "s|TARGET_GROUP_ARN=.*|TARGET_GROUP_ARN=\"${NEW_TARGET_GROUP_ARN}\"|" .env
sed -i.bak "s|METRIC_DISCOVERY_ALB_ARN=.*|METRIC_DISCOVERY_ALB_ARN=\"${METRIC_DISCOVERY_ALB_ARN}\"|" .env
sed -i.bak "s|METRIC_DISCOVERY_LISTENER_ARN=.*|METRIC_DISCOVERY_LISTENER_ARN=\"${METRIC_DISCOVERY_LISTENER_ARN}\"|" .env

echo "Migration complete! New configuration:"
echo "New target group ARN: ${NEW_TARGET_GROUP_ARN}"
echo "Using ALB: ${METRIC_DISCOVERY_ALB_ARN}"
echo "Using Listener: ${METRIC_DISCOVERY_LISTENER_ARN}"
echo ""
echo "Next steps:"
echo "1. Update your FastAPI application code to handle the new path prefix /${METRIC_DISCOVERY_APP_NAME}/*"
echo "2. Monitor the ECS service status in AWS console"
echo "3. Test your application using the new URL path"