locals {
}

terraform {
  backend "s3" {
    bucket         = "ceresgalax-tf-state"
    key            = "barbot/terraform.tfstate"
    region         = "us-west-2"

    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}
