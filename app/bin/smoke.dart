// ignore_for_file: avoid_print, avoid_relative_lib_imports
// End-to-end smoke test: sign in via Cognito SRP, fetch the briefing.
// Proves auth + JWT + API Gateway authorizer + Lambda + DynamoDB all connect.
// Run: dart run bin/smoke.dart <password>
import '../lib/api.dart';
import '../lib/auth.dart';

Future<void> main(List<String> args) async {
  final pw = args.isNotEmpty ? args[0] : 'Copilot#2026';
  final auth = Auth();
  print('Signing in...');
  await auth.signIn('ashishkosana@gmail.com', pw);
  print('Signed in: ${auth.isSignedIn}');
  final b = await Api(auth).briefing();
  print('needs-you: ${b.needsAction.length} · jobs: ${b.jobs.length}');
  for (final j in b.jobs.take(6)) {
    print('  ${j.score}%  ${j.title} @ ${j.company}');
  }
}
