// Typed briefing models parsed from the API response.
//
// Parsing is lenient: DynamoDB numbers come back JSON-encoded as strings
// ("87"), so numeric fields are coerced via toString() -> int.tryParse.

int _asInt(Object? v) => int.tryParse('${v ?? 0}') ?? 0;
String _str(Object? v) => (v ?? '').toString();

class JobMatch {
  const JobMatch({
    required this.title,
    required this.company,
    required this.location,
    required this.url,
    required this.score,
  });

  final String title;
  final String company;
  final String location;
  final String url;
  final int score;

  factory JobMatch.fromJson(Map<String, dynamic> j) => JobMatch(
        title: _str(j['title']),
        company: _str(j['company']),
        location: _str(j['location']),
        url: _str(j['url']),
        score: _asInt(j['score']),
      );
}

class ActionItem {
  const ActionItem({required this.from, required this.subject, required this.status});

  final String from;
  final String subject;
  final String status;

  /// Sender display name without the `<email>` part.
  String get who => from.split('<').first.trim().isEmpty ? from : from.split('<').first.trim();

  factory ActionItem.fromJson(Map<String, dynamic> j) => ActionItem(
        from: _str(j['from']),
        subject: _str(j['subject']),
        status: _str(j['status']),
      );
}

class Briefing {
  const Briefing({
    required this.day,
    required this.needsAction,
    required this.jobs,
    required this.pipeline,
    required this.scanned,
    required this.noise,
  });

  final String day;
  final List<ActionItem> needsAction;
  final List<JobMatch> jobs;
  final Map<String, int> pipeline;
  final int scanned;
  final int noise;

  bool get isEmpty => needsAction.isEmpty && jobs.isEmpty && pipeline.isEmpty;

  factory Briefing.fromJson(Map<String, dynamic> j) {
    List<T> list<T>(String key, T Function(Map<String, dynamic>) f) =>
        ((j[key] as List?) ?? const [])
            .map((e) => f(Map<String, dynamic>.from(e as Map)))
            .toList();
    final pipeline = <String, int>{};
    (j['pipeline'] as Map?)?.forEach((k, v) => pipeline['$k'] = _asInt(v));
    return Briefing(
      day: _str(j['date']),
      needsAction: list('needs_action', ActionItem.fromJson),
      jobs: list('jobs', JobMatch.fromJson),
      pipeline: pipeline,
      scanned: _asInt(j['scanned']),
      noise: _asInt(j['noise']),
    );
  }
}
