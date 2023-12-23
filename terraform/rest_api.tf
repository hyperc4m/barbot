resource "aws_api_gateway_account" "account" {
  cloudwatch_role_arn = aws_iam_role.api_gateway_cloudwatch_global.arn
}

resource "aws_iam_role" "api_gateway_cloudwatch_global" {
  name = "barbot_api_gateway_cloudwatch_global"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "apigateway.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy" "cloudwatch" {
  name = "default"
  role = aws_iam_role.api_gateway_cloudwatch_global.id

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:PutLogEvents",
                "logs:GetLogEvents",
                "logs:FilterLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
EOF
}

data aws_iam_policy_document "apigateway_lambda_invoker_assume_role" {
  statement {
    effect = "Allow"
    principals {
      identifiers = ["apigateway.amazonaws.com"]
      type        = "Service"
    }
    principals {
      identifiers = ["scheduler.amazonaws.com"]
      type        = "Service"
    }
    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "apigateway_lambda_invoker" {
  name = "barbot_apigateway_lambda_invoker"
  assume_role_policy = data.aws_iam_policy_document.apigateway_lambda_invoker_assume_role.json
}

resource "aws_iam_role_policy" "apigateway_lambda_invoker" {
  name = "default"
  role = aws_iam_role.apigateway_lambda_invoker.id

  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "*"
        }
    ]
}
EOF
}


resource "aws_apigatewayv2_api" "barbot" {
  name = "barbot"
  protocol_type = "HTTP"


}

#
# Deployment
#

#resource "aws_apigatewayv2_deployment" "barbot" {
#  api_id = aws_apigatewayv2_api.barbot.id
#
#
#  depends_on = [
#    aws_apigatewayv2_authorizer.barbot,
#    aws_apigatewayv2_route.webhook,
#    aws_apigatewayv2_integration.webhook
##    aws_api_gateway_resource.webhook,
##    aws_api_gateway_method.webhook_post,
##    aws_api_gateway_integration.webhook_post
#  ]
#
##  triggers = {
##    redeployment = [
##      aws_apigatewayv2_authorizer.barbot,
##      aws_apigatewayv2_route.webhook,
##      aws_apigatewayv2_integration.webhook
##    ]
##  }
#
#
#
##  triggers = {
##    // TODO: This sucks and is hacky
##    redeployment = filesha1("rest_api_schema.tf")
##  }
#
#  lifecycle {
#    create_before_destroy = true
#  }
#}

#
# Stage and Stage Settings
#

resource "aws_apigatewayv2_stage" "barbot" {
  name    = "barbot"
  # deployment_id = aws_apigatewayv2_deployment.barbot.id
  api_id   = aws_apigatewayv2_api.barbot.id
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.apigateway.arn
    format          = "$context.identity.sourceIp - - [$context.requestTime] \"$context.httpMethod $context.routeKey $context.protocol\" $context.status $context.responseLength $context.requestId -- $context.authorizer.error"
  }

  auto_deploy = true
}

resource "aws_cloudwatch_log_group" "apigateway" {
  name = "barbot-apigateway"
}


#
# Authorizer
#

resource "aws_apigatewayv2_authorizer" "barbot" {
  name                   = "barbot"
  api_id                 = aws_apigatewayv2_api.barbot.id
  authorizer_type        = "REQUEST"
  authorizer_uri         = aws_lambda_function.authorizer.invoke_arn
  authorizer_credentials_arn = aws_iam_role.apigateway_lambda_invoker.arn
  # identity_validation_expression = "^.+"
  identity_sources        = ["$request.header.X-Telegram-Bot-Api-Secret-Token"]
  authorizer_payload_format_version = "2.0"
  enable_simple_responses = true
}
