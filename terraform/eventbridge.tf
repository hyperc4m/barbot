locals {
  schedules = {
    first_reminder = {
      cron       = var.first_reminder_cron
      event_type = "AskForSuggestions"
    }
    create_poll = {
      cron       = var.create_poll_cron
      event_type = "CreatePoll"
    }
    last_call = {
      cron       = var.last_call_cron
      event_type = "PollReminder"
    }
    close_poll = {
      cron       = var.close_poll_cron
      event_type = "ChooseWinner"
    }
  }
}



resource "aws_scheduler_schedule" "first_reminder" {
  for_each = local.schedules

  name = "${var.prefix}_${each.key}"
  group_name = "default"
  schedule_expression = "cron(${each.value.cron})"
  schedule_expression_timezone = var.timezone

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn = aws_lambda_function.api["sequence"].arn
    role_arn = aws_iam_role.apigateway_lambda_invoker.arn
    input = <<EOF
{
  "barnight_event_type": "${each.value.event_type}"
}
EOF

    retry_policy {
      maximum_event_age_in_seconds = 60 * 60 * 1  # hours
    }

  }
}