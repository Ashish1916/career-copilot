import 'package:amazon_cognito_identity_dart_2/cognito.dart';

import 'config.dart';

/// Thin Cognito wrapper (SRP auth, pure Dart — no native Amplify pods).
/// Mirrors the Crewtron auth pattern: sign in, then hand the ID token to the
/// Dio interceptor for every API call.
class Auth {
  Auth() : _pool = CognitoUserPool(Config.userPoolId, Config.userPoolClientId);

  final CognitoUserPool _pool;
  CognitoUserSession? _session;
  String? _email;

  bool get isSignedIn => _session?.isValid() ?? false;

  Future<void> signIn(String email, String password) async {
    final user = CognitoUser(email, _pool);
    final details =
        AuthenticationDetails(username: email, password: password);
    _session = await user.authenticateUser(details);
    _email = email;
  }

  /// Fresh ID token for the Authorization header (refreshes if needed).
  Future<String?> idToken() async {
    if (_session == null) return null;
    if (_session!.isValid()) return _session!.getIdToken().getJwtToken();
    // Refresh with the stored refresh token.
    final user = CognitoUser(_email, _pool);
    _session = await user.refreshSession(_session!.getRefreshToken()!);
    return _session!.getIdToken().getJwtToken();
  }

  void signOut() {
    _session = null;
    _email = null;
  }
}
