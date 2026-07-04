/// Backend configuration — points at the career-copilot AWS stack
/// (personal account, us-east-1). These are public client identifiers, not
/// secrets: the Cognito app client has no secret and the API is authorizer-gated.
class Config {
  static const apiBase =
      'https://9iidni6dml.execute-api.us-east-1.amazonaws.com/prod';
  static const region = 'us-east-1';
  static const userPoolId = 'us-east-1_hl1Q14NSE';
  static const userPoolClientId = '70mo9su908mp5gvm7o98v3bruq';
}
