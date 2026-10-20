import 'package:appflowy/plugins/document/presentation/editor_plugins/ai/ai_writer_block_component.dart';
import 'package:appflowy/plugins/document/presentation/editor_plugins/ai/operations/ai_writer_entities.dart';
import 'package:appflowy_editor/appflowy_editor.dart';
import 'package:flutter/material.dart';

/// AI Writer shortcut
///
/// - support
///   - desktop
///
final CommandShortcutEvent aiShortcutEvent = CommandShortcutEvent(
  key: 'ai summary',
  getDescription: () => 'AI Writer',
  command: 'ctrl+j',
  handler: _aiShortcutHandler,
);

CommandShortcutEventHandler _aiShortcutHandler = (editorState) {
  final selection = editorState.selection?.normalized;
  if (selection == null) {
    return KeyEventResult.ignored;
  }

  _insertAiNode(editorState, AiWriterCommand.userQuestion);
  return KeyEventResult.handled;
};

void _insertAiNode(EditorState editorState, AiWriterCommand command) async {
  final selection = editorState.selection?.normalized;
  if (selection == null) {
    return;
  }

  final transaction = editorState.transaction
    ..insertNode(
      selection.end.path.next,
      aiWriterNode(
        selection: selection,
        command: command,
      ),
    )
    ..selectionExtraInfo = {selectionExtraInfoDisableToolbar: true};

  await editorState.apply(
    transaction,
    options: const ApplyOptions(
      recordUndo: false,
      inMemoryUpdate: true,
    ),
    withUpdateSelection: false,
  );
}
