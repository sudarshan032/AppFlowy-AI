import 'dart:async';
import 'package:appflowy/ai/ai_agent_client.dart';
import 'package:appflowy/plugins/database/domain/field_service.dart';
import 'package:appflowy/plugins/document/application/document_data_pb_extension.dart';
import 'package:appflowy/shared/icon_emoji_picker/flowy_icon_emoji_picker.dart';
import 'package:appflowy/shared/markdown_to_document.dart';
import 'package:appflowy/workspace/application/view/view_service.dart';
import 'package:appflowy_backend/log.dart';
import 'package:appflowy_backend/protobuf/flowy-database2/protobuf.dart';
import 'package:appflowy_backend/protobuf/flowy-folder/view.pbenum.dart';
import 'package:bloc/bloc.dart';
import 'package:flutter/foundation.dart';

/// State for the AI chat feature.
@immutable
sealed class AiChatState {
  const AiChatState();
}

class AiChatIdleState extends AiChatState {
  const AiChatIdleState({this.messages = const []});
  final List<ChatMessage> messages;
}

class AiChatLoadingState extends AiChatState {
  const AiChatLoadingState({required this.messages});
  final List<ChatMessage> messages;
}

class AiChatErrorState extends AiChatState {
  const AiChatErrorState({required this.messages, required this.error});
  final List<ChatMessage> messages;
  final String error;
}

/// A chat message in the AI chat.
class ChatMessage {
  const ChatMessage({
    required this.content,
    required this.isUser,
    this.timestamp,
  });

  final String content;
  final bool isUser;
  final DateTime? timestamp;
}

/// Cubit for managing AI chat state.
class AiChatCubit extends Cubit<AiChatState> {
  AiChatCubit({
    required this.workspaceId,
    required this.currentViewId,
  }) : super(const AiChatIdleState()) {
    // Load existing databases to prevent duplicates
    _refreshExistingDatabases();
  }

  final String workspaceId;
  final String currentViewId;
  final AiAgentClient _client = AiAgentClient();
  
  // Track created database names to avoid duplicates (case-insensitive)
  final Set<String> _existingDatabases = {};

  /// Load existing databases from the workspace to prevent duplicates
  /// Clears and reloads each time to catch deletions
  Future<void> _refreshExistingDatabases() async {
    _existingDatabases.clear();
    try {
      final result = await ViewBackendService.getChildViews(viewId: workspaceId);
      result.fold(
        (views) {
          for (final view in views) {
            // Only add non-empty names
            if (view.name.trim().isNotEmpty) {
              _existingDatabases.add(view.name.toLowerCase().trim());
              Log.debug('[AiChatCubit] Found existing view: ${view.name}');
            }
          }
        },
        (error) {
          Log.error('[AiChatCubit] Failed to load existing views: $error');
        },
      );
    } catch (e) {
      Log.error('[AiChatCubit] Error loading existing databases: $e');
    }
  }

  List<ChatMessage> get messages {
    final state = this.state;
    if (state is AiChatIdleState) return state.messages;
    if (state is AiChatLoadingState) return state.messages;
    if (state is AiChatErrorState) return state.messages;
    return [];
  }

  /// Sends a message to the AI agent.
  Future<void> sendMessage(String message) async {
    if (message.trim().isEmpty) return;

    final userMessage = ChatMessage(
      content: message,
      isUser: true,
      timestamp: DateTime.now(),
    );

    final updatedMessages = [...messages, userMessage];
    emit(AiChatLoadingState(messages: updatedMessages));

    try {
      final response = await _client.sendPrompt(
        prompt: message,
        objectId: currentViewId,
        workspaceId: workspaceId,
      );

      if (response.isSuccess) {
        // Handle any actions from the agent
        String aiMessageContent = response.message;
        
        for (final action in response.actions) {
          final result = await _handleAction(action);
          if (result != null) {
            aiMessageContent = result;
          }
        }

        final aiMessage = ChatMessage(
          content: aiMessageContent,
          isUser: false,
          timestamp: DateTime.now(),
        );

        emit(AiChatIdleState(messages: [...updatedMessages, aiMessage]));
      } else {
        final aiMessage = ChatMessage(
          content: response.error ?? 'Something went wrong',
          isUser: false,
          timestamp: DateTime.now(),
        );
        emit(AiChatIdleState(messages: [...updatedMessages, aiMessage]));
      }
    } catch (e) {
      Log.error('[AiChatCubit] Error: $e');
      final aiMessage = ChatMessage(
        content: 'Error: $e',
        isUser: false,
        timestamp: DateTime.now(),
      );
      emit(AiChatIdleState(messages: [...updatedMessages, aiMessage]));
    }
  }

  /// Handles an action from the AI agent. Returns a message if applicable.
  Future<String?> _handleAction(Map<String, dynamic> action) async {
    final actionType = action['action_type'];
    Log.debug('[AiChatCubit] Handling action: $actionType');

    switch (actionType) {
      case 'create_database':
        return await _createDatabase(action);
      case 'insert_block':
        Log.debug('[AiChatCubit] insert_block action - delegating to document');
        return null;

      // Schema modification actions - actually modify AppFlowy
      case 'add_field':
        return await _addField(action);
      case 'drop_field':
        return await _dropField(action);
      case 'rename_field':
        return await _renameField(action);
      case 'list_fields':
        return _formatListFieldsMessage(action);

      // Record operations
      case 'edit_record':
        return action['message']?.toString() ?? 'Record updated.';
      case 'delete_record':
        return action['message']?.toString() ?? 'Record deleted.';

      // Database deletion
      case 'delete_database':
        return await _deleteDatabase(action);

      // Page creation
      case 'create_page':
        return await _createPage(action);

      case 'schema_modified':  // Legacy fallback
      case 'display_results':  // Legacy fallback
        return action['message']?.toString();

      // Error handling
      case 'error':
        final message = action['message']?.toString() ?? 'An error occurred';
        return '⚠️ $message';

      // Text response (for writing/explain actions)
      case 'text_response':
        return action['response']?.toString() ?? action['message']?.toString();

      default:
        // Fallback: display the message from the action if available
        if (action.containsKey('message')) {
          return action['message'].toString();
        }
        if (action.containsKey('response')) {
          return action['response'].toString();
        }
        Log.debug('[AiChatCubit] Unknown action type: $actionType');
        return null;
    }
  }

  /// Formats a list fields response
  String _formatListFieldsMessage(Map<String, dynamic> action) {
    final message = action['message']?.toString() ?? '';
    final properties = action['properties'] as List<dynamic>?;
    
    if (properties != null && properties.isNotEmpty) {
      final buffer = StringBuffer();
      buffer.writeln('📋 $message');
      buffer.writeln('');
      for (final prop in properties) {
        if (prop is Map) {
          final name = prop['name'] ?? 'Unknown';
          final type = prop['type'] ?? 'text';
          buffer.writeln('  • **$name** ($type)');
        }
      }
      return buffer.toString();
    }
    
    return '📋 $message';
  }


  /// Maps agent property types to AppFlowy FieldType
  FieldType _mapPropertyType(String? type) {
    switch (type?.toLowerCase()) {
      case 'number':
        return FieldType.Number;
      case 'date':
        return FieldType.DateTime;
      case 'checkbox':
      case 'boolean':
        return FieldType.Checkbox;
      case 'select':
        return FieldType.SingleSelect;
      case 'multiselect':
        return FieldType.MultiSelect;
      case 'url':
        return FieldType.URL;
      case 'text':
      default:
        return FieldType.RichText;
    }
  }

  /// Creates a database via ViewBackendService and adds custom fields.
  Future<String> _createDatabase(Map<String, dynamic> action) async {
    // Extract name from message like "Database 'Sales Dashboard' created."
    final message = action['message']?.toString() ?? '';
    String name = '';
    
    // Try to extract name from message using regex
    final regex = RegExp(r"Database '([^']+)' created");
    final match = regex.firstMatch(message);
    if (match != null && match.groupCount >= 1) {
      name = match.group(1) ?? '';
    }
    
    // If name is empty, try to get it from the user's original request
    if (name.isEmpty) {
      // Try common patterns like "customers database", "a database called X"
      final patterns = [
        RegExp(r'(?:create|make|add)\s+(?:a\s+)?(\w+)\s+database', caseSensitive: false),
        RegExp(r'database\s+(?:called|named)\s+(\w+)', caseSensitive: false),
      ];
      
      for (final pattern in patterns) {
        // Check if we can find the name in the action's message context
        final msgMatch = pattern.firstMatch(message);
        if (msgMatch != null && msgMatch.groupCount >= 1) {
          name = msgMatch.group(1) ?? '';
          if (name.isNotEmpty) break;
        }
      }
    }
    
    // Final fallback if still empty
    if (name.isEmpty) {
      name = 'New Database';
    }
    
    // Capitalize first letter
    name = name[0].toUpperCase() + name.substring(1);
    
    final normalizedName = name.toLowerCase().trim();
    
    // Refresh the list of existing databases before checking (catches deletions)
    await _refreshExistingDatabases();
    
    // Check for duplicates (case-insensitive)
    if (_existingDatabases.contains(normalizedName)) {
      Log.debug('[AiChatCubit] Database "$name" already exists, skipping');
      return '⚠️ Database "$name" already exists! Try a different name.';
    }
    
    Log.debug('[AiChatCubit] Creating AppFlowy database: $name');

    // Create under the workspace root
    final result = await ViewBackendService.createView(
      layoutType: ViewLayoutPB.Grid,
      parentViewId: workspaceId,
      name: name,
    );

    return await result.fold(
      (view) async {
        _existingDatabases.add(normalizedName);
        Log.debug('[AiChatCubit] ✅ AppFlowy database created: ${view.id} - $name');

        // Set icon if provided
        final icon = action['icon']?.toString();
        if (icon != null && icon.isNotEmpty) {
          await ViewBackendService.updateViewIcon(
            view: view,
            viewIcon: EmojiIconData.emoji(icon),
          );
        }

        // Get properties from the action
        final properties = action['properties'] as List<dynamic>? ?? [];
        
        // Get all fields first
        final fieldsResult = await FieldBackendService.getFields(viewId: view.id);
        await fieldsResult.fold(
          (fields) async {
            for (final field in fields) {
              // Rename primary field "Name" to "ID"
              if (field.name == 'Name' && field.isPrimary) {
                Log.debug('[AiChatCubit] Renaming primary field to ID');
                final fieldService = FieldBackendService(
                  viewId: view.id,
                  fieldId: field.id,
                );
                await fieldService.updateField(name: 'ID');
              }
              // Delete Type and Done columns
              else if (field.name == 'Type' || field.name == 'Done') {
                Log.debug('[AiChatCubit] Deleting default field: ${field.name}');
                await FieldBackendService.deleteField(
                  viewId: view.id,
                  fieldId: field.id,
                );
              }
            }
          },
          (error) {
            Log.error('[AiChatCubit] Failed to get fields: $error');
          },
        );

        
        int createdFields = 0;
        
        // Add custom fields for each property
        for (final prop in properties) {
          if (prop is Map) {
            final fieldName = prop['name']?.toString();
            final fieldType = _mapPropertyType(prop['type']?.toString());
            
            if (fieldName != null && fieldName.isNotEmpty) {
              Log.debug('[AiChatCubit] Adding field: $fieldName (${prop['type']})');
              
              final fieldResult = await FieldBackendService.createField(
                viewId: view.id,
                fieldType: fieldType,
                fieldName: fieldName,
              );

              
              fieldResult.fold(
                (field) {
                  Log.debug('[AiChatCubit] ✅ Field created: ${field.name}');
                  createdFields++;
                },
                (error) {
                  Log.error('[AiChatCubit] ❌ Failed to create field $fieldName: $error');
                },
              );

            }
          }
        }

        
        if (properties.isNotEmpty) {
          return '✅ Database "$name" created with ${createdFields} custom properties!';
        }
        return '✅ Database "$name" created successfully!';
      },
      (error) {
        Log.error('[AiChatCubit] ❌ Failed to create database: $error');
        return '❌ Failed to create database: ${error.msg}';
      },
    );
  }

  /// Finds a workspace child view by name (case-insensitive).
  Future<String?> _findViewIdByName(String name) async {
    try {
      final result = await ViewBackendService.getChildViews(viewId: workspaceId);
      return result.fold(
        (views) {
          for (final view in views) {
            if (view.name.toLowerCase().trim() == name.toLowerCase().trim()) {
              return view.id;
            }
          }
          return null;
        },
        (error) => null,
      );
    } catch (e) {
      return null;
    }
  }

  /// Adds a field to an existing AppFlowy database.
  Future<String> _addField(Map<String, dynamic> action) async {
    final dbName = action['db_name']?.toString();
    final fieldName = action['field_name']?.toString();
    final fieldType = action['field_type']?.toString();
    final message = action['message']?.toString() ?? 'Field added.';

    if (dbName == null || fieldName == null) {
      return '➕ $message';
    }

    final viewId = await _findViewIdByName(dbName);
    if (viewId == null) {
      return '➕ $message (AppFlowy view not found for sync)';
    }

    final result = await FieldBackendService.createField(
      viewId: viewId,
      fieldType: _mapPropertyType(fieldType),
      fieldName: fieldName,
    );

    return result.fold(
      (field) {
        Log.debug('[AiChatCubit] ✅ Field added to AppFlowy: ${field.name}');
        return '➕ $message';
      },
      (error) {
        Log.error('[AiChatCubit] ❌ Failed to add field in AppFlowy: $error');
        return '➕ $message (backend updated, AppFlowy sync failed)';
      },
    );
  }

  /// Drops a field from an existing AppFlowy database.
  Future<String> _dropField(Map<String, dynamic> action) async {
    final dbName = action['db_name']?.toString();
    final fieldName = action['field_name']?.toString();
    final message = action['message']?.toString() ?? 'Field removed.';

    if (dbName == null || fieldName == null) {
      return '🗑️ $message';
    }

    final viewId = await _findViewIdByName(dbName);
    if (viewId == null) {
      return '🗑️ $message (AppFlowy view not found for sync)';
    }

    final fieldsResult = await FieldBackendService.getFields(viewId: viewId);
    return await fieldsResult.fold(
      (fields) async {
        for (final field in fields) {
          if (field.name.toLowerCase() == fieldName.toLowerCase()) {
            await FieldBackendService.deleteField(
              viewId: viewId,
              fieldId: field.id,
            );
            Log.debug('[AiChatCubit] ✅ Field dropped from AppFlowy: $fieldName');
            return '🗑️ $message';
          }
        }
        return '🗑️ $message (field not found in AppFlowy)';
      },
      (error) {
        Log.error('[AiChatCubit] ❌ Failed to drop field in AppFlowy: $error');
        return '🗑️ $message (backend updated, AppFlowy sync failed)';
      },
    );
  }

  /// Renames a field in an existing AppFlowy database.
  Future<String> _renameField(Map<String, dynamic> action) async {
    final dbName = action['db_name']?.toString();
    final oldName = action['old_name']?.toString();
    final newName = action['new_name']?.toString();
    final message = action['message']?.toString() ?? 'Field renamed.';

    if (dbName == null || oldName == null || newName == null) {
      return '✏️ $message';
    }

    final viewId = await _findViewIdByName(dbName);
    if (viewId == null) {
      return '✏️ $message (AppFlowy view not found for sync)';
    }

    final fieldsResult = await FieldBackendService.getFields(viewId: viewId);
    return await fieldsResult.fold(
      (fields) async {
        for (final field in fields) {
          if (field.name.toLowerCase() == oldName.toLowerCase()) {
            final fieldService = FieldBackendService(
              viewId: viewId,
              fieldId: field.id,
            );
            await fieldService.updateField(name: newName);
            Log.debug('[AiChatCubit] ✅ Field renamed in AppFlowy: $oldName -> $newName');
            return '✏️ $message';
          }
        }
        return '✏️ $message (field not found in AppFlowy)';
      },
      (error) {
        Log.error('[AiChatCubit] ❌ Failed to rename field in AppFlowy: $error');
        return '✏️ $message (backend updated, AppFlowy sync failed)';
      },
    );
  }

  /// Deletes a database view from AppFlowy.
  Future<String> _deleteDatabase(Map<String, dynamic> action) async {
    final dbName = action['db_name']?.toString();
    final message = action['message']?.toString() ?? 'Database deleted.';

    if (dbName == null) {
      return '🗑️ $message';
    }

    final viewId = await _findViewIdByName(dbName);
    if (viewId == null) {
      // Already deleted from backend, just update tracking
      _existingDatabases.remove(dbName.toLowerCase().trim());
      return '🗑️ $message';
    }

    final result = await ViewBackendService.deleteView(viewId: viewId);
    return result.fold(
      (unit) {
        _existingDatabases.remove(dbName.toLowerCase().trim());
        Log.debug('[AiChatCubit] ✅ Database deleted from AppFlowy: $dbName');
        return '🗑️ $message';
      },
      (error) {
        Log.error('[AiChatCubit] ❌ Failed to delete view in AppFlowy: $error');
        return '🗑️ $message (backend deleted, AppFlowy sync failed)';
      },
    );
  }

  /// Creates a page in AppFlowy from structured content blocks.
  /// Converts content blocks → markdown → Document → bytes for initial content.
  Future<String> _createPage(Map<String, dynamic> action) async {
    final title = action['title']?.toString() ?? 'Untitled';
    final icon = action['icon']?.toString() ?? '📄';
    final content = action['content'];
    final message = action['message']?.toString() ?? 'Page created.';

    // Convert structured content blocks to markdown
    final markdown = _contentBlocksToMarkdown(content, title);

    // Convert markdown → Document → DocumentDataPB → bytes
    List<int>? initialBytes;
    try {
      final document = customMarkdownToDocument(markdown);
      initialBytes = DocumentDataPBFromTo.fromDocument(document)?.writeToBuffer();
    } catch (e) {
      Log.error('[AiChatCubit] Failed to convert content to document bytes: $e');
    }

    try {
      final result = await ViewBackendService.createView(
        layoutType: ViewLayoutPB.Document,
        parentViewId: workspaceId,
        name: title,
        initialDataBytes: initialBytes,
      );

      return await result.fold(
        (view) async {
          Log.debug('[AiChatCubit] ✅ Page created in AppFlowy: ${view.id} - $title');

          // Set icon
          if (icon.isNotEmpty) {
            await ViewBackendService.updateViewIcon(
              view: view,
              viewIcon: EmojiIconData.emoji(icon),
            );
          }

          return '📄 $message';
        },
        (error) {
          Log.error('[AiChatCubit] ❌ Failed to create page: $error');
          return '📄 $message (backend created, AppFlowy sync failed)';
        },
      );
    } catch (e) {
      Log.error('[AiChatCubit] ❌ Error creating page: $e');
      return '📄 $message (backend created, AppFlowy sync failed)';
    }
  }

  /// Converts structured content blocks to markdown string.
  String _contentBlocksToMarkdown(dynamic content, String title) {
    final buffer = StringBuffer();
    buffer.writeln('# $title');
    buffer.writeln();

    if (content == null || content is! Map) return buffer.toString();

    final blocks = content['blocks'] as List<dynamic>? ?? [];

    for (final block in blocks) {
      if (block is! Map) continue;
      final type = block['type']?.toString() ?? '';

      switch (type) {
        case 'heading':
          final level = block['level'] as int? ?? 1;
          final prefix = '#' * level;
          buffer.writeln('$prefix ${block['text'] ?? ''}');
          buffer.writeln();
        case 'paragraph':
          buffer.writeln(block['text'] ?? '');
          buffer.writeln();
        case 'bullet_list':
          final items = block['items'] as List<dynamic>? ?? [];
          for (final item in items) {
            buffer.writeln('- $item');
          }
          buffer.writeln();
        case 'todo':
          final checked = block['checked'] == true;
          final checkbox = checked ? '[x]' : '[ ]';
          buffer.writeln('- $checkbox ${block['text'] ?? ''}');
        default:
          if (block.containsKey('text')) {
            buffer.writeln(block['text']);
            buffer.writeln();
          }
      }
    }

    return buffer.toString();
  }

  /// Clears the chat history.
  void clearMessages() {
    emit(const AiChatIdleState());
  }
}
