import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../services/api_service.dart';
import 'package:url_launcher/url_launcher.dart'; // Понадобится для открытия ссылок

class AppleNewsWidget extends StatefulWidget {
  const AppleNewsWidget({super.key});

  @override
  State<AppleNewsWidget> createState() => _AppleNewsWidgetState();
}

class _AppleNewsWidgetState extends State<AppleNewsWidget> {
  List<dynamic> _news = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadNews();
  }

  Future<void> _loadNews() async {
    try {
      final api = Provider.of<ApiService>(context, listen: false);
      final news = await api.getAppleNews();
      if (mounted) {
        setState(() {
          _news = news;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(24), // Скругление как у компаса
        border: Border.all(
          color: isDark ? Colors.grey.shade800 : Colors.grey.shade200,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.newspaper, color: isDark ? Colors.blue.shade300 : Colors.blue.shade700, size: 20),
              const SizedBox(width: 8),
              const Text(
                'Новости Apple',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_isLoading)
            const Center(child: Padding(padding: EdgeInsets.all(20), child: CircularProgressIndicator()))
          else if (_news.isEmpty)
            const Text('Новости не найдены', style: TextStyle(color: Colors.grey))
          else
            ..._news.map((item) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 12.0),
                child: InkWell(
                  onTap: () async {
                    final url = Uri.parse(item['url'] ?? '');
                    if (await canLaunchUrl(url)) {
                      await launchUrl(url, mode: LaunchMode.externalApplication);
                    }
                  },
                  borderRadius: BorderRadius.circular(8),
                  child: Padding(
                    padding: const EdgeInsets.all(4.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          item['title'] ?? '',
                          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, height: 1.3),
                          maxLines: 3,
                          overflow: TextOverflow.ellipsis,
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Text(
                              item['source'] ?? '',
                              style: TextStyle(color: isDark ? Colors.blue.shade300 : Colors.blue.shade700, fontSize: 11, fontWeight: FontWeight.w500),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              // Тут можно отформатировать дату, но для простоты оставим как есть
                              (item['published_at'] ?? '').toString().substring(0, 10),
                              style: TextStyle(color: Colors.grey.shade500, fontSize: 11),
                            ),
                          ],
                        ),
                        const Divider(height: 20, thickness: 0.5),
                      ],
                    ),
                  ),
                ),
              );
            }).toList(),
        ],
      ),
    );
  }
}