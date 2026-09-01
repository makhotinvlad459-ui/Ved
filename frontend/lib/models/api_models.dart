// frontend/lib/models/api_models.dart

class PendingModel {
  final int id;
  final String partNumber;
  final String description;
  final int? suggestedCategoryId;
  final String? suggestedCategoryName;
  final int? suggestedColorId;
  final String? suggestedColorName;
  final String suggestedNameRu;

  PendingModel({
    required this.id,
    required this.partNumber,
    required this.description,
    this.suggestedCategoryId,
    this.suggestedCategoryName,
    this.suggestedColorId,
    this.suggestedColorName,
    required this.suggestedNameRu,
  });

  factory PendingModel.fromJson(Map<String, dynamic> json) {
    return PendingModel(
      id: json['id'],
      partNumber: json['part_number'] ?? '',
      description: json['description'] ?? '',
      suggestedCategoryId: json['suggested_category_id'],
      suggestedCategoryName: json['suggested_category_name'],
      suggestedColorId: json['suggested_color_id'],
      suggestedColorName: json['suggested_color_name'],
      suggestedNameRu: json['suggested_name_ru'] ?? '',
    );
  }
}