output "telegram_bot_token" {
  value = var.telegram_bot_token
  sensitive = true
}

output "webhook_url" {
  value = "${aws_apigatewayv2_stage.barbot.invoke_url}/${local.webhook_path}"
}

output "webhook_secret" {
  value = random_password.webhook_secret.result
  sensitive = true
}