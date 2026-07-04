// End-to-end smoke test: sign in via Cognito SRP, fetch the briefing.
// Proves auth + JWT + API Gateway authorizer + Lambda + DynamoDB all connect.
// Run: dart run bin/smoke.dart <password>
import '../lib/auth.dart';
import '../lib/api.dart';

Future<void> main(List<String> args) async {
  final pw = args.isNotEmpty ? args[0] : 'Copilot#2026';
  final auth = Auth();
  print('Signing in...');
  await auth.signIn('ashishkosana@gmail.com', pw);
  print('Signed in: ${auth.isSignedIn}');
  final data = await Api(auth).briefing();
  final md = (data['markdown'] as String?) ?? '(none)';
  print('--- briefing (${md.length} chars) ---');
  print(md.split('\n').take(8).join('\n'));
}
