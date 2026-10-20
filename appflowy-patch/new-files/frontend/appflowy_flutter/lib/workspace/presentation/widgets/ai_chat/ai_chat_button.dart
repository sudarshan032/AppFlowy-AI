import 'package:appflowy/workspace/application/ai_chat/ai_chat_cubit.dart';
import 'package:appflowy/workspace/presentation/widgets/ai_chat/ai_chat_overlay.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

/// A floating button that opens the AI chat overlay.
/// Positioned at the bottom-right corner of the screen.
/// Uses OverlayEntry so user can still interact with the app while chat is open.
class FloatingAiChatButton extends StatefulWidget {
  const FloatingAiChatButton({
    super.key,
    required this.workspaceId,
    required this.currentViewId,
  });

  final String workspaceId;
  final String currentViewId;

  @override
  State<FloatingAiChatButton> createState() => _FloatingAiChatButtonState();
}

class _FloatingAiChatButtonState extends State<FloatingAiChatButton> {
  OverlayEntry? _overlayEntry;
  bool _isChatOpen = false;
  
  // Persist cubit across opens/closes
  late final AiChatCubit _chatCubit;

  @override
  void initState() {
    super.initState();
    _chatCubit = AiChatCubit(
      workspaceId: widget.workspaceId,
      currentViewId: widget.currentViewId,
    );
  }

  @override
  void dispose() {
    _closeChat();
    _chatCubit.close();
    super.dispose();
  }

  void _toggleChat() {
    if (_isChatOpen) {
      _closeChat();
    } else {
      _openChat();
    }
  }

  void _openChat() {
    if (_isChatOpen) return;

    _overlayEntry = OverlayEntry(
      builder: (context) => BlocProvider.value(
        value: _chatCubit,
        child: AiChatOverlayPanel(
          onClose: _closeChat,
        ),
      ),
    );

    Overlay.of(context).insert(_overlayEntry!);
    setState(() => _isChatOpen = true);
  }

  void _closeChat() {
    _overlayEntry?.remove();
    _overlayEntry = null;
    if (mounted) {
      setState(() => _isChatOpen = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      right: 24,
      bottom: 80,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(28),
          onTap: _toggleChat,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: _isChatOpen
                    ? [const Color(0xFF764BA2), const Color(0xFF667EEA)]
                    : [const Color(0xFF667EEA), const Color(0xFF764BA2)],
              ),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFF667EEA).withOpacity(_isChatOpen ? 0.5 : 0.3),
                  blurRadius: _isChatOpen ? 16 : 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Icon(
              _isChatOpen ? Icons.close : Icons.auto_awesome,
              color: Colors.white,
              size: 28,
            ),
          ),
        ),
      ),
    );
  }
}
