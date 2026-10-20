import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:appflowy_backend/log.dart';

/// HTTP client for communicating with the AI agent backend.
class AiAgentClient {
  AiAgentClient({this.baseUrl = 'http://127.0.0.1:8001'});

  final String baseUrl;

  /// Sends a prompt to the AI agent and returns the response.
  Future<AiAgentResponse> sendPrompt({
    required String prompt,
    required String objectId,
    required String workspaceId,
    String? viewName,
    String? viewType,
  }) async {
    try {
      Log.debug('[AiAgentClient] Sending prompt: $prompt');

      final context = <String, dynamic>{
        'object_id': objectId,
        'workspace_id': workspaceId,
      };
      if (viewName != null && viewName.isNotEmpty) {
        context['view_name'] = viewName;
      }
      if (viewType != null && viewType.isNotEmpty) {
        context['view_type'] = viewType;
      }

      final response = await http.post(
        Uri.parse('$baseUrl/run-prompt'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'text': prompt,
          'context': context,
          'scope': 'page',
        }),
      ).timeout(const Duration(seconds: 60));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        Log.debug('[AiAgentClient] Response: $data');
        return AiAgentResponse.success(data);
      } else {
        Log.error('[AiAgentClient] Error: ${response.statusCode} - ${response.body}');
        return AiAgentResponse.error('Server error: ${response.statusCode}');
      }
    } catch (e) {
      Log.error('[AiAgentClient] Exception: $e');
      return AiAgentResponse.error('Connection error: $e');
    }
  }

  /// Checks if the agent server is running.
  Future<bool> isHealthy() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/health'),
      ).timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (e) {
      return false;
    }
  }
}

class AiAgentResponse {
  AiAgentResponse._({
    required this.isSuccess,
    this.data,
    this.error,
  });

  factory AiAgentResponse.success(dynamic data) => AiAgentResponse._(
        isSuccess: true,
        data: data,
      );

  factory AiAgentResponse.error(String error) => AiAgentResponse._(
        isSuccess: false,
        error: error,
      );

  final bool isSuccess;
  final dynamic data;
  final String? error;

  String get message {
    if (isSuccess && data != null) {
      // Try to get message from result.message
      if (data is Map && data.containsKey('result')) {
        final result = data['result'];
        if (result is Map && result.containsKey('message')) {
          return result['message'].toString();
        }
      }
      if (data is Map && data.containsKey('response')) {
        return data['response'].toString();
      }
      return data.toString();
    }
    return error ?? 'Unknown error';
  }

  /// Returns the action type from the result (e.g., create_database, insert_block)
  String? get actionType {
    if (isSuccess && data != null && data is Map && data.containsKey('result')) {
      final result = data['result'];
      if (result is Map) {
        return result['action_type']?.toString();
      }
    }
    return null;
  }

  /// Returns the result data as a map
  Map<String, dynamic> get resultData {
    if (isSuccess && data != null && data is Map && data.containsKey('result')) {
      final result = data['result'];
      if (result is Map) {
        return Map<String, dynamic>.from(result);
      }
    }
    return {};
  }

  List<Map<String, dynamic>> get actions {
    // If there's a result with action_type, treat it as a single action
    if (actionType != null) {
      return [resultData];
    }
    // Fallback: check for explicit actions array
    if (isSuccess && data != null && data is Map && data.containsKey('actions')) {
      return List<Map<String, dynamic>>.from(data['actions'] ?? []);
    }
    return [];
  }
}
