#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { CareerCopilotStack } from "../lib/career-copilot-stack";

const app = new cdk.App();
new CareerCopilotStack(app, "career-copilot", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION || "us-east-1",
  },
});
