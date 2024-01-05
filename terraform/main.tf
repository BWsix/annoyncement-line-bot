locals {
  bot_dir             = "${path.module}/../derek"
  dynamodb_table_name = "${var.project_name}-groups"
}

provider "aws" {
  region                   = var.aws_region
  shared_credentials_files = [var.credentials_path]
}

provider "archive" {}

data "aws_iam_policy_document" "lambda_linebot_policy" {
  statement {
    sid    = ""
    effect = "Allow"

    principals {
      identifiers = ["lambda.amazonaws.com"]
      type        = "Service"
    }

    actions = ["sts:AssumeRole"]
  }
}

resource "aws_iam_role" "lambda" {
  name               = "${var.project_name}-default-iam-for-lambda"
  assume_role_policy = data.aws_iam_policy_document.lambda_linebot_policy.json
}

module "layer" {
  source              = "git::https://github.com/enter-at/terraform-aws-lambda-layer.git?ref=main"
  layer_name          = "${var.project_name}-dependencies"
  package_file        = "${local.bot_dir}/requirements.txt"
  compatible_runtimes = [var.runtime]
}

// lambda
data "archive_file" "lambda_source" {
  type        = "zip"
  output_path = "archives/lambda.zip"
  source_dir  = local.bot_dir
  excludes    = ["venv"]
}

resource "aws_lambda_function" "linebot" {
  function_name = "${var.project_name}-linebot"

  filename         = data.archive_file.lambda_source.output_path
  source_code_hash = data.archive_file.lambda_source.output_base64sha256

  role    = aws_iam_role.lambda.arn
  handler = "bot.handle_lambda"
  runtime = var.runtime
  timeout = 30

  layers = ["${module.layer.arn}"]

  environment {
    variables = {
      LINEBOT_ACCESS_TOKEN = var.linebot_access_token
      LINEBOT_SECRET       = var.linebot_secret
      DASHBOARD_URL        = var.dashboard_url
      DYNAMODB_TABLE_NAME  = local.dynamodb_table_name
    }
  }
}

resource "aws_lambda_function" "dashboard" {
  function_name = "${var.project_name}-dashboard"

  filename         = data.archive_file.lambda_source.output_path
  source_code_hash = data.archive_file.lambda_source.output_base64sha256

  role    = aws_iam_role.lambda.arn
  handler = "dashboard.handle_lambda"
  runtime = var.runtime
  timeout = 30

  layers = ["${module.layer.arn}"]

  environment {
    variables = {
      LINEBOT_ACCESS_TOKEN = var.linebot_access_token
      LINEBOT_SECRET       = var.linebot_secret
      DYNAMODB_TABLE_NAME  = local.dynamodb_table_name
    }
  }
}

resource "aws_cloudwatch_log_group" "lambda_linebot" {
  name              = "/aws/lambda/${aws_lambda_function.linebot.function_name}"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "lambda_dashboard" {
  name              = "/aws/lambda/${aws_lambda_function.dashboard.function_name}"
  retention_in_days = 14
}

resource "aws_iam_role_policy_attachment" "lambda_linebot" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

// api gateway
resource "aws_api_gateway_rest_api" "api_gateway" {
  name = var.project_name
}

// api gateway for linebot
resource "aws_api_gateway_resource" "linebot" {
  rest_api_id = aws_api_gateway_rest_api.api_gateway.id
  parent_id   = aws_api_gateway_rest_api.api_gateway.root_resource_id
  path_part   = "linebot"
}

// api gateway for dashboard
resource "aws_api_gateway_resource" "dashboard" {
  rest_api_id = aws_api_gateway_rest_api.api_gateway.id
  parent_id   = aws_api_gateway_rest_api.api_gateway.root_resource_id
  path_part   = "dashboard"
}

resource "aws_api_gateway_method" "linebot" {
  rest_api_id   = aws_api_gateway_rest_api.api_gateway.id
  resource_id   = aws_api_gateway_resource.linebot.id
  http_method   = "ANY"
  authorization = "NONE"
}

resource "aws_api_gateway_method" "dashboard" {
  rest_api_id   = aws_api_gateway_rest_api.api_gateway.id
  resource_id   = aws_api_gateway_resource.dashboard.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_linebot" {
  rest_api_id = aws_api_gateway_rest_api.api_gateway.id
  resource_id = aws_api_gateway_method.linebot.resource_id
  http_method = aws_api_gateway_method.linebot.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.linebot.invoke_arn
}

resource "aws_api_gateway_integration" "lambda_dashboard" {
  rest_api_id = aws_api_gateway_rest_api.api_gateway.id
  resource_id = aws_api_gateway_method.dashboard.resource_id
  http_method = aws_api_gateway_method.dashboard.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.dashboard.invoke_arn
}

resource "aws_api_gateway_deployment" "v1" {
  rest_api_id = aws_api_gateway_rest_api.api_gateway.id
  depends_on = [
    aws_api_gateway_integration.lambda_linebot,
    aws_api_gateway_integration.lambda_dashboard,
  ]
  triggers = {
    redeployment = sha1(jsonencode(aws_api_gateway_rest_api.api_gateway.body))
  }
  stage_name = "v1"
}

output "webhook_url" {
  value = "${aws_api_gateway_deployment.v1.invoke_url}/linebot"
}

output "dashbaoard_api" {
  value = "${aws_api_gateway_deployment.v1.invoke_url}/dashboard"
}

resource "aws_lambda_permission" "gateway_may_call_lambda_linebot" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.linebot.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_api_gateway_rest_api.api_gateway.execution_arn}/*"
}

resource "aws_lambda_permission" "gateway_may_call_lambda_dashboard" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.dashboard.function_name
  principal     = "apigateway.amazonaws.com"

  source_arn = "${aws_api_gateway_rest_api.api_gateway.execution_arn}/*"
}


resource "aws_dynamodb_table" "groups" {
  name           = local.dynamodb_table_name
  read_capacity  = 1
  write_capacity = 1
  hash_key       = "group_id"

  attribute {
    name = "group_id"
    type = "S"
  }
}

data "aws_iam_policy_document" "lambda_may_use_database" {
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:*"]
    resources = [aws_dynamodb_table.groups.arn]
  }
}

resource "aws_iam_role_policy" "lambda_may_use_database" {
  name   = "dynamodb_lambda_policy"
  role   = aws_iam_role.lambda.id
  policy = data.aws_iam_policy_document.lambda_may_use_database.json
}

module "cors" {
  source  = "squidfunk/api-gateway-enable-cors/aws"
  version = "0.3.3"

  api_id          = aws_api_gateway_rest_api.api_gateway.id
  api_resource_id = aws_api_gateway_resource.dashboard.id
}
