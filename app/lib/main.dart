import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api.dart';
import 'auth.dart';

// --- Providers (Crewtron-style: wiring providers + a state notifier) --------
final authProvider = Provider<Auth>((ref) => Auth());
final apiProvider = Provider<Api>((ref) => Api(ref.read(authProvider)));

/// Loads the latest briefing markdown. Re-fetched on pull-to-refresh / sign-in.
final briefingProvider = FutureProvider.autoDispose<String>((ref) async {
  final data = await ref.read(apiProvider).briefing();
  return (data['markdown'] as String?) ?? 'No briefing yet.';
});

const _indigo = Color(0xFF4F46E5);

void main() => runApp(const ProviderScope(child: CopilotApp()));

class CopilotApp extends StatelessWidget {
  const CopilotApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Career Copilot',
        theme: ThemeData(colorSchemeSeed: _indigo, useMaterial3: true),
        home: const SignInPage(),
      );
}

class SignInPage extends ConsumerStatefulWidget {
  const SignInPage({super.key});
  @override
  ConsumerState<SignInPage> createState() => _SignInPageState();
}

class _SignInPageState extends ConsumerState<SignInPage> {
  final _email = TextEditingController(text: 'ashishkosana@gmail.com');
  final _password = TextEditingController();
  bool _loading = false;
  String? _error;

  Future<void> _signIn() async {
    setState(() { _loading = true; _error = null; });
    try {
      await ref.read(authProvider).signIn(_email.text.trim(), _password.text);
      if (mounted) {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(builder: (_) => const BriefingPage()),
        );
      }
    } catch (e) {
      setState(() => _error = 'Sign-in failed: $e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text('Career Copilot',
                    textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 30, fontWeight: FontWeight.w800, color: _indigo)),
                const SizedBox(height: 6),
                const Text('Your daily job-search briefing',
                    textAlign: TextAlign.center, style: TextStyle(color: Colors.black54)),
                const SizedBox(height: 32),
                TextField(controller: _email, decoration: const InputDecoration(labelText: 'Email', border: OutlineInputBorder())),
                const SizedBox(height: 14),
                TextField(controller: _password, obscureText: true, decoration: const InputDecoration(labelText: 'Password', border: OutlineInputBorder())),
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _loading ? null : _signIn,
                  style: FilledButton.styleFrom(backgroundColor: _indigo, padding: const EdgeInsets.symmetric(vertical: 16)),
                  child: _loading
                      ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Text('Sign in'),
                ),
                if (_error != null) Padding(padding: const EdgeInsets.only(top: 16), child: Text(_error!, style: const TextStyle(color: Colors.red))),
              ],
            ),
          ),
        ),
      );
}

class BriefingPage extends ConsumerWidget {
  const BriefingPage({super.key});
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final briefing = ref.watch(briefingProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Today'),
        backgroundColor: _indigo,
        foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: () => ref.invalidate(briefingProvider)),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(briefingProvider),
        child: briefing.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (e, _) => ListView(children: [Padding(padding: const EdgeInsets.all(24), child: Text('Could not load briefing:\n$e'))]),
          data: (md) => Markdown(data: md, padding: const EdgeInsets.all(20)),
        ),
      ),
    );
  }
}
