import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as secrets from "aws-cdk-lib/aws-secretsmanager";
import * as path from "path";

export class CareerCopilotStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Single-table store: briefings, jobs (dedup), pipeline.
    const table = new dynamodb.Table(this, "Table", {
      tableName: "career-copilot",
      partitionKey: { name: "PK", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "SK", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // Gmail OAuth material (credentials + token JSON). Seeded out-of-band.
    const gmailSecret = new secrets.Secret(this, "GmailSecret", {
      secretName: "career-copilot/gmail",
      description: "Gmail OAuth credentials.json + token.json for the agent",
    });

    // Bundle only src/ (career_copilot pkg + its requirements.txt) — keeps
    // .venv, infra/, and any local credentials out of the deployment artifact.
    const src = path.join(__dirname, "..", "..", "src");
    const common = {
      runtime: lambda.Runtime.PYTHON_3_13,
      entry: src,
      index: "career_copilot/lambda_handler.py",
      environment: {
        TABLE_NAME: table.tableName,
        GMAIL_SECRET_ID: gmailSecret.secretName,
      },
      timeout: cdk.Duration.seconds(60),
      memorySize: 256,
    };

    // Daily cron: fetch inbox -> triage -> store briefing -> email.
    const cronFn = new PythonFunction(this, "CronFn", {
      ...common,
      handler: "cron_handler",
      environment: { ...common.environment, MY_EMAIL: "ashishkosana@gmail.com" },
      timeout: cdk.Duration.seconds(120),
    });
    table.grantReadWriteData(cronFn);
    gmailSecret.grantRead(cronFn);

    new events.Rule(this, "DailyRule", {
      // 07:00 America/Phoenix = 14:00 UTC (AZ has no DST).
      schedule: events.Schedule.cron({ minute: "0", hour: "14" }),
      targets: [new targets.LambdaFunction(cronFn)],
    });

    // API: GET /briefing -> latest stored briefing (for the Flutter app).
    const apiFn = new PythonFunction(this, "ApiFn", {
      ...common,
      handler: "api_handler",
    });
    table.grantReadData(apiFn);

    const api = new apigw.RestApi(this, "Api", {
      restApiName: "career-copilot",
      defaultCorsPreflightOptions: {
        allowOrigins: apigw.Cors.ALL_ORIGINS,
        allowMethods: apigw.Cors.ALL_METHODS,
      },
    });
    api.root
      .addResource("briefing")
      .addMethod("GET", new apigw.LambdaIntegration(apiFn));

    new cdk.CfnOutput(this, "ApiUrl", { value: api.url });
    new cdk.CfnOutput(this, "GmailSecretName", { value: gmailSecret.secretName });
  }
}
