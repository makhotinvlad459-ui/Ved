// frontend/lib/screens/shipment_detail_screen.dart
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';

class ShipmentDetailScreen extends StatefulWidget {
  final int shipmentId;
  const ShipmentDetailScreen({super.key, required this.shipmentId});

  @override
  State<ShipmentDetailScreen> createState() => _ShipmentDetailScreenState();
}

class _ShipmentDetailScreenState extends State<ShipmentDetailScreen> {
  Map<String, dynamic>? _shipment;
  List<dynamic> _tasks = [];
  bool _isLoading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _loadShipment();
  }

  Future<void> _loadShipment() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final shipment = await api.getShipment(widget.shipmentId);
      final tasks = await api.getShipmentTasks(widget.shipmentId); // <-- НОВЫЙ МЕТОД
      setState(() {
        _shipment = shipment;
        _tasks = tasks;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = 'Ошибка загрузки: $e';
        _isLoading = false;
      });
    }
  }

  Future<void> _toggleTask(int taskId, bool currentValue) async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      await api.updateTask(taskId: taskId, isDone: !currentValue);
      await _loadShipment();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Ошибка: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _updateComment(int taskId, String comment) async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      await api.updateTask(taskId: taskId, comment: comment);
      await _loadShipment();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('❌ Ошибка: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_shipment?['shipment_number'] ?? 'Поставка'),
        backgroundColor: Colors.white,
        foregroundColor: Colors.black,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context, true),
        ),
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error.isNotEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(Icons.error, color: Colors.red, size: 48),
                      const SizedBox(height: 16),
                      Text(_error),
                      ElevatedButton(
                        onPressed: _loadShipment,
                        child: const Text('Повторить'),
                      ),
                    ],
                  ),
                )
              : Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildShipmentInfo(),
                      const SizedBox(height: 16),
                      _buildProgress(),
                      const SizedBox(height: 16),
                      Expanded(
                        child: _tasks.isEmpty
                            ? const Center(child: Text('Нет задач'))
                            : ListView.builder(
                                itemCount: _tasks.length,
                                itemBuilder: (context, index) {
                                  return _buildTaskItem(_tasks[index]);
                                },
                              ),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _buildShipmentInfo() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey[50],
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _shipment?['shipment_number'] ?? '',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text('Инвойс: ${_shipment?['invoice_number'] ?? '—'}'),
          Text('Поставщик: ${_shipment?['supplier'] ?? '—'}'),
          Text('Статус: ${_shipment?['status'] == 'completed' ? '✅ Завершена' : '🔄 В процессе'}'),
        ],
      ),
    );
  }

  Widget _buildProgress() {
    final progress = _shipment?['progress'] ?? 0;
    return Row(
      children: [
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress / 100,
              backgroundColor: Colors.grey[200],
              color: progress >= 80
                  ? Colors.green
                  : progress >= 50
                      ? Colors.orange
                      : Colors.blue,
              minHeight: 8,
            ),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          '$progress%',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            color: progress >= 80 ? Colors.green : Colors.blue,
          ),
        ),
      ],
    );
  }

  Widget _buildTaskItem(dynamic task) {
    final isDone = task['is_done'] ?? false;
    final hasParent = task['parent_task'] != null && task['parent_task'] != '';

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Row(
          children: [
            if (hasParent) const SizedBox(width: 24),
            Checkbox(
              value: isDone,
              onChanged: (value) {
                if (value != null) {
                  _toggleTask(task['id'], isDone);
                }
              },
              activeColor: Colors.green,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    task['task_name'] ?? '',
                    style: TextStyle(
                      fontSize: 14,
                      decoration: isDone
                          ? TextDecoration.lineThrough
                          : TextDecoration.none,
                      color: isDone ? Colors.grey : Colors.black,
                    ),
                  ),
                  if (task['comment'] != null &&
                      task['comment'].toString().isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        '💬 ${task['comment']}',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey[600],
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ),
                ],
              ),
            ),
            IconButton(
              icon: const Icon(Icons.comment_outlined, size: 20),
              onPressed: () {
                _showCommentDialog(task['id'], task['comment'] ?? '');
              },
              tooltip: 'Добавить комментарий',
            ),
          ],
        ),
      ),
    );
  }

  void _showCommentDialog(int taskId, String currentComment) {
    final controller = TextEditingController(text: currentComment);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Комментарий'),
        content: TextField(
          controller: controller,
          maxLines: 3,
          decoration: const InputDecoration(
            hintText: 'Введите комментарий...',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Отмена'),
          ),
          ElevatedButton(
            onPressed: () {
              _updateComment(taskId, controller.text);
              Navigator.pop(context);
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.blue,
              foregroundColor: Colors.white,
            ),
            child: const Text('Сохранить'),
          ),
        ],
      ),
    );
  }
}