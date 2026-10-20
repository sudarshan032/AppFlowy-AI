import 'dart:convert';
import 'package:http/http.dart' as http;

class AIPluginService {
  // Use 10.0.2.2 for Android emulator, localhost for iOS/Desktop
  // For now assuming Desktop (macOS) as per user environment
  static const String _baseUrl = 'http://127.0.0.1:8001';

  static Future<String> summarize(String content) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/ai/writing/summarize'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'text': content, 
          'style': 'concise',
          'max_sentences': 3
        }),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['result'] as String;
      } else {
        throw Exception('Failed to summarize: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('AI Plugin Error: $e');
    }
  }

  static Future<String> improveWriting(String content) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/ai/writing/improve'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'text': content}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return data['result'] as String;
      } else {
        throw Exception('Failed to improve writing: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('AI Plugin Error: $e');
    }
  }
}
