
resource "aws_dynamodb_table" "barnight_week" {
  name         = "${var.prefix}_week"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_dynamodb_table" "barnight_events" {
  name         = "${var.prefix}_events"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

resource "aws_dynamodb_table_item" "current_week" {
  table_name = aws_dynamodb_table.barnight_week.name
  hash_key = aws_dynamodb_table.barnight_week.hash_key
  item = <<EOF
{
  "id": {"S": "current"},
  "venues": {"M": {} }
}
EOF

  lifecycle {
    ignore_changes = [item]
  }
}

resource "aws_dynamodb_table_item" "current_events" {
  table_name = aws_dynamodb_table.barnight_events.name
  hash_key = aws_dynamodb_table.barnight_events.hash_key
  item = <<EOF
{
  "id": {"S": "current"},
  "events": {"M": {} }
}
EOF

  lifecycle {
    ignore_changes = [item]
  }
}
