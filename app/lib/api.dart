import 'package:dio/dio.dart';

import 'auth.dart';
import 'config.dart';
import 'models.dart';

/// Dio client with a JWT interceptor — attaches the Cognito ID token to every
/// request, exactly like the Crewtron dio_client + jwt_auth_interceptor.
class Api {
  Api(this._auth) {
    _dio = Dio(BaseOptions(baseUrl: Config.apiBase))
      ..interceptors.add(InterceptorsWrapper(onRequest: (options, handler) async {
        final token = await _auth.idToken();
        if (token != null) options.headers['Authorization'] = 'Bearer $token';
        handler.next(options);
      }));
  }

  final Auth _auth;
  late final Dio _dio;

  /// GET /briefing -> today's structured briefing.
  Future<Briefing> briefing() async {
    final res = await _dio.get('/briefing');
    return Briefing.fromJson(Map<String, dynamic>.from(res.data as Map));
  }
}
