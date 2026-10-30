// frontend/lib/screens/ai_assistant_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';

import '../services/api_service.dart';

// ============================================================
// МОДЕЛИ СООБЩЕНИЙ
// ============================================================

enum AiMsgType { user, answer, confirmation, result, error }

class _AiMessage {
  final AiMsgType type;
  final String text;
  final String? actionId;
  final Map<String, dynamic>? preview;
  final List<String>? toolsUsed;
  final DateTime createdAt;
  bool resolved; // для confirmation: подтверждено/отменено/истекло

  _AiMessage({
    required this.type,
    required this.text,
    this.actionId,
    this.preview,
    this.toolsUsed,
    DateTime? createdAt,
    this.resolved = false,
  }) : createdAt = createdAt ?? DateTime.now();
}

// ============================================================
// ЭКРАН
// ============================================================

class AiAssistantScreen extends StatefulWidget {
  const AiAssistantScreen({super.key});

  @override
  State<AiAssistantScreen> createState() => _AiAssistantScreenState();
}

class _AiAssistantScreenState extends State<AiAssistantScreen> {
  final _inputController = TextEditingController();
  final _scrollController = ScrollController();
  final _focusNode = FocusNode();

  final List<_AiMessage> _messages = [];
  bool _isSending = false;

  static const _quickPrompts = [
    'Сколько товаров в базе?',
    'Какие категории есть?',
    'Проверь артикулы ABC123, XYZ789',
    'Найди sport band',
    'Кто тебя сделал?',
    'Расскажи анекдот',
  ];

  @override
  void dispose() {
    _inputController.dispose();
    _scrollController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _send(String text) async {
    final t = text.trim();
    if (t.isEmpty || _isSending) return;

    setState(() {
      _messages.add(_AiMessage(type: AiMsgType.user, text: t));
      _isSending = true;
    });
    _inputController.clear();
    _scrollToBottom();

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = await api.aiCommand(t);

      if (!mounted) return;

      final type = (result['type'] ?? 'answer') as String;

      if (type == 'confirmation') {
        setState(() {
          _messages.add(_AiMessage(
            type: AiMsgType.confirmation,
            text: result['text'] ?? 'Подтвердить действие?',
            actionId: result['action_id'],
            preview: result['preview'],
            toolsUsed: _asStringList(result['tools_used']),
          ));
        });
      } else if (type == 'error') {
        setState(() {
          _messages.add(_AiMessage(
            type: AiMsgType.error,
            text: result['text'] ?? 'Ошибка',
          ));
        });
      } else {
        setState(() {
          _messages.add(_AiMessage(
            type: AiMsgType.answer,
            text: result['text'] ?? '',
            toolsUsed: _asStringList(result['tools_used']),
          ));
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _messages.add(_AiMessage(
          type: AiMsgType.error,
          text: '$e',
        ));
      });
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
        _scrollToBottom();
        _focusNode.requestFocus();
      }
    }
  }

  List<String>? _asStringList(dynamic v) {
    if (v is List) {
      return v.map((e) => e.toString()).toList();
    }
    return null;
  }

  Future<void> _confirm(_AiMessage msg, bool approved) async {
    if (msg.actionId == null || msg.resolved) return;

    setState(() => _isSending = true);

    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final result = approved
          ? await api.aiConfirm(actionId: msg.actionId!, approved: true)
          : await api.aiCancel(msg.actionId!);

      if (!mounted) return;

      final type = (result['type'] ?? 'result') as String;
      final text = (result['text'] ?? '').toString();

      setState(() {
        msg.resolved = true;
        if (type == 'result') {
          _messages.add(_AiMessage(type: AiMsgType.result, text: text));
        } else if (type == 'cancelled') {
          _messages.add(_AiMessage(
            type: AiMsgType.answer,
            text: text.isNotEmpty ? text : 'Отменено.',
          ));
        } else {
          _messages.add(_AiMessage(type: AiMsgType.error, text: text));
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _messages.add(_AiMessage(type: AiMsgType.error, text: '$e'));
      });
    } finally {
      if (mounted) {
        setState(() => _isSending = false);
        _scrollToBottom();
      }
    }
  }

  void _copyMessage(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('✅ Скопировано'),
        backgroundColor: Colors.green,
        duration: Duration(seconds: 1),
      ),
    );
  }

  void _clearChat() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Очистить историю?'),
        content: const Text('Все сообщения будут удалены.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Отмена'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Очистить', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    ).then((ok) {
      if (ok == true && mounted) {
        setState(() => _messages.clear());
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [Colors.deepPurple.shade600, Colors.deepPurple.shade300],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(9),
              ),
              child: const Icon(Icons.auto_awesome, color: Colors.white, size: 18),
            ),
            const SizedBox(width: 10),
            const Text('AI-ассистент'),
          ],
        ),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          if (_messages.isNotEmpty)
            IconButton(
              tooltip: 'Очистить историю',
              icon: const Icon(Icons.delete_sweep_outlined),
              onPressed: _clearChat,
            ),
        ],
      ),
      body: Column(
        children: [
          Expanded(child: _buildMessages()),
          _buildInput(),
        ],
      ),
    );
  }

  // ============================================================
  // СПИСОК СООБЩЕНИЙ
  // ============================================================

  Widget _buildMessages() {
    if (_messages.isEmpty) {
      return _buildEmptyState();
    }
    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      itemCount: _messages.length + (_isSending ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == _messages.length) {
          return _buildThinkingIndicator();
        }
        return _buildMessageBubble(_messages[index]);
      },
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 88,
              height: 88,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [Colors.deepPurple.shade600, Colors.deepPurple.shade300],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(24),
                boxShadow: [
                  BoxShadow(
                    color: Colors.deepPurple.shade100,
                    blurRadius: 20,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              child: const Icon(Icons.auto_awesome,
                  color: Colors.white, size: 44),
            ),
            const SizedBox(height: 20),
            const Text(
              'AI-ассистент VED',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Спроси о товарах, обнови веса, проверь артикулы',
              style: TextStyle(color: Colors.grey),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 28),
            const Text(
              'Попробуй:',
              style: TextStyle(
                fontSize: 13,
                color: Colors.grey,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: _quickPrompts.map((p) {
                return ActionChip(
                  avatar: const Icon(Icons.north_west, size: 14),
                  label: Text(p, style: const TextStyle(fontSize: 12)),
                  onPressed: () => _send(p),
                  backgroundColor: Colors.white,
                  side: BorderSide(color: Colors.grey.shade300),
                );
              }).toList(),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildThinkingIndicator() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        children: [
          _avatar(Colors.deepPurple),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: Colors.grey.shade100,
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
                const SizedBox(width: 10),
                Text(
                  'Думаю...',
                  style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _avatar(Color color) {
    return Container(
      width: 28,
      height: 28,
      decoration: BoxDecoration(
        color: color.withOpacity(0.15),
        shape: BoxShape.circle,
      ),
      child: Icon(Icons.auto_awesome, size: 16, color: color),
    );
  }

  Widget _buildMessageBubble(_AiMessage m) {
    switch (m.type) {
      case AiMsgType.user:
        return _bubbleUser(m);
      case AiMsgType.answer:
        return _bubbleAi(m, iconColor: Colors.blueGrey);
      case AiMsgType.result:
        return _bubbleAi(m, iconColor: Colors.green);
      case AiMsgType.error:
        return _bubbleAi(m, iconColor: Colors.red, isError: true);
      case AiMsgType.confirmation:
        return _bubbleConfirmation(m);
    }
  }

  Widget _bubbleUser(_AiMessage m) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [Colors.blue.shade600, Colors.blue.shade400],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(16),
                  topRight: Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                  bottomRight: Radius.circular(4),
                ),
              ),
              child: SelectableText(
                m.text,
                style: const TextStyle(color: Colors.white, fontSize: 14, height: 1.4),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: Colors.blue.shade50,
              shape: BoxShape.circle,
            ),
            child: Icon(Icons.person, size: 16, color: Colors.blue.shade700),
          ),
        ],
      ),
    );
  }

  Widget _bubbleAi(_AiMessage m, {required Color iconColor, bool isError = false}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _avatar(iconColor),
          const SizedBox(width: 8),
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isError ? Colors.red.shade50 : Colors.white,
                border: Border.all(
                  color: isError ? Colors.red.shade200 : Colors.grey.shade200,
                ),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(4),
                  topRight: Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                  bottomRight: Radius.circular(16),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SelectableText(
                    m.text,
                    style: TextStyle(
                      fontSize: 14,
                      height: 1.45,
                      color: isError ? Colors.red.shade900 : Colors.black87,
                    ),
                  ),
                  if (m.toolsUsed != null && m.toolsUsed!.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 8),
                      child: Wrap(
                        spacing: 6,
                        runSpacing: 4,
                        children: m.toolsUsed!.map((t) {
                          return Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.blueGrey.shade50,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              t,
                              style: TextStyle(
                                fontSize: 10,
                                color: Colors.blueGrey.shade700,
                                fontFamily: 'monospace',
                              ),
                            ),
                          );
                        }).toList(),
                      ),
                    ),
                  const SizedBox(height: 4),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      InkWell(
                        onTap: () => _copyMessage(m.text),
                        borderRadius: BorderRadius.circular(6),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 4),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.copy_rounded,
                                  size: 13, color: Colors.grey.shade600),
                              const SizedBox(width: 4),
                              Text(
                                'Копировать',
                                style: TextStyle(
                                  fontSize: 11,
                                  color: Colors.grey.shade600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _bubbleConfirmation(_AiMessage m) {
    final preview = m.preview ?? {};
    final items = (preview['items'] as List?) ?? [];
    final count = preview['count'] ?? items.length;
    final isResolved = m.resolved;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _avatar(Colors.orange),
          const SizedBox(width: 8),
          Flexible(
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white,
                border: Border.all(color: Colors.orange.shade200),
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(4),
                  topRight: Radius.circular(16),
                  bottomLeft: Radius.circular(16),
                  bottomRight: Radius.circular(16),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 10),
                    decoration: BoxDecoration(
                      color: Colors.orange.shade50,
                      borderRadius: const BorderRadius.only(
                        topRight: Radius.circular(16),
                        topLeft: Radius.circular(4),
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.warning_amber_rounded,
                            size: 18, color: Colors.orange.shade800),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            m.text,
                            style: TextStyle(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: Colors.orange.shade900,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.all(14),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Затронется: $count',
                          style: const TextStyle(
                              fontSize: 13, color: Colors.grey),
                        ),
                        if (items.isNotEmpty) ...[
                          const SizedBox(height: 10),
                          ConstrainedBox(
                            constraints: const BoxConstraints(maxHeight: 220),
                            child: Container(
                              decoration: BoxDecoration(
                                color: Colors.grey.shade50,
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: ListView.separated(
                                shrinkWrap: true,
                                itemCount: items.length,
                                separatorBuilder: (_, __) =>
                                    Divider(height: 1, color: Colors.grey.shade200),
                                itemBuilder: (context, idx) {
                                  final it = items[idx] as Map<String, dynamic>;
                                  return Padding(
                                    padding: const EdgeInsets.symmetric(
                                        horizontal: 10, vertical: 8),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          it['part_number']?.toString() ?? '',
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w600,
                                            fontSize: 12,
                                            fontFamily: 'monospace',
                                          ),
                                        ),
                                        const SizedBox(height: 2),
                                        Text(
                                          it['description']?.toString() ?? '',
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontSize: 11,
                                            color: Colors.grey.shade700,
                                          ),
                                        ),
                                        if (it.containsKey('old_weight') ||
                                            it.containsKey('new_weight'))
                                          Padding(
                                            padding: const EdgeInsets.only(top: 4),
                                            child: Text(
                                              '${it['old_weight'] ?? '—'} кг → ${it['new_weight']} кг',
                                              style: TextStyle(
                                                fontSize: 11,
                                                color: Colors.orange.shade800,
                                                fontWeight: FontWeight.w500,
                                              ),
                                            ),
                                          ),
                                      ],
                                    ),
                                  );
                                },
                              ),
                            ),
                          ),
                        ],
                        const SizedBox(height: 14),
                        if (isResolved)
                          Row(
                            children: [
                              Icon(Icons.check_circle,
                                  size: 16, color: Colors.green.shade600),
                              const SizedBox(width: 6),
                              Text(
                                'Обработано',
                                style: TextStyle(
                                  fontSize: 13,
                                  color: Colors.green.shade700,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          )
                        else
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton.icon(
                                  onPressed: _isSending
                                      ? null
                                      : () => _confirm(m, false),
                                  icon: const Icon(Icons.close, size: 16),
                                  label: const Text('Отмена'),
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: Colors.grey.shade700,
                                    side: BorderSide(color: Colors.grey.shade300),
                                    padding:
                                        const EdgeInsets.symmetric(vertical: 10),
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                flex: 2,
                                child: ElevatedButton.icon(
                                  onPressed: _isSending
                                      ? null
                                      : () => _confirm(m, true),
                                  icon: const Icon(Icons.check, size: 16),
                                  label: const Text('Подтвердить'),
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.orange,
                                    foregroundColor: Colors.white,
                                    padding:
                                        const EdgeInsets.symmetric(vertical: 10),
                                  ),
                                ),
                              ),
                            ],
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // ПОЛЕ ВВОДА
  // ============================================================

  Widget _buildInput() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.grey.shade200)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 10,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Container(
              constraints: const BoxConstraints(maxHeight: 140),
              decoration: BoxDecoration(
                color: Colors.grey.shade100,
                borderRadius: BorderRadius.circular(22),
              ),
              child: TextField(
                controller: _inputController,
                focusNode: _focusNode,
                minLines: 1,
                maxLines: 5,
                textInputAction: TextInputAction.send,
                onSubmitted: _send,
                decoration: const InputDecoration(
                  hintText: 'Спроси что-нибудь...',
                  border: InputBorder.none,
                  contentPadding:
                      EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                ),
                style: const TextStyle(fontSize: 14),
              ),
            ),
          ),
          const SizedBox(width: 8),
          Material(
            color: _isSending ? Colors.grey.shade300 : Colors.deepPurple,
            borderRadius: BorderRadius.circular(22),
            child: InkWell(
              onTap: _isSending
                  ? null
                  : () => _send(_inputController.text),
              borderRadius: BorderRadius.circular(22),
              child: Container(
                width: 44,
                height: 44,
                alignment: Alignment.center,
                child: _isSending
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.arrow_upward,
                        color: Colors.white, size: 20),
              ),
            ),
          ),
        ],
      ),
    );
  }
}