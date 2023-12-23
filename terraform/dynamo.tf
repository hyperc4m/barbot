
resource "aws_dynamodb_table" "barnight_week" {
  name         = "barnight_week"
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
