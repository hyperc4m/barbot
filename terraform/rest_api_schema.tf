locals {
  webhook_path = "webhook"
}

resource "aws_apigatewayv2_route" "webhook" {
  api_id             = aws_apigatewayv2_api.barbot.id
  route_key          = "POST /${local.webhook_path}"
  authorization_type = "CUSTOM"
  authorizer_id      = aws_apigatewayv2_authorizer.barbot.id
  target             = "integrations/${aws_apigatewayv2_integration.webhook.id}"
}

resource "aws_apigatewayv2_integration" "webhook" {
  api_id = aws_apigatewayv2_api.barbot.id
  integration_type = "AWS_PROXY"
  integration_method = "POST"
  integration_uri = aws_lambda_function.api["webhook"].invoke_arn
  credentials_arn = aws_iam_role.apigateway_lambda_invoker.arn
  payload_format_version = "2.0"
}
