from django.core.management.base import BaseCommand
from products.models import Category, CategoryAttributeTemplate


class Command(BaseCommand):
    help = 'Setup default category attribute templates for dynamic product fields'

    def handle(self, *args, **kwargs):
        
        self.stdout.write(self.style.WARNING('Setting up category attribute templates...'))
        
        # Define category-specific attributes
        category_attributes = {
            
            # =============================
            # COSMETICS
            # =============================
            'Cosmetics': [
                {'key': 'shade_color', 'label': 'Shade/Color', 'type': 'text', 'required': False, 'order': 1,
                 'placeholder': 'e.g., Fair, Medium, Dark', 'help': 'Product shade or color'},
                
                {'key': 'skin_type', 'label': 'Skin Type', 'type': 'select', 'required': False, 'order': 2,
                 'options': 'Dry,Oily,Normal,Combination,All Types', 'help': 'Suitable skin type'},
                
                {'key': 'ingredients', 'label': 'Key Ingredients', 'type': 'textarea', 'required': False, 'order': 3,
                 'placeholder': 'List main ingredients', 'help': 'Main active ingredients'},
                
                {'key': 'net_quantity', 'label': 'Net Quantity', 'type': 'text', 'required': True, 'order': 4,
                 'placeholder': 'e.g., 50ml, 100g', 'help': 'Product volume/weight'},
                
                {'key': 'expiry_date', 'label': 'Expiry Date', 'type': 'date', 'required': False, 'order': 5,
                 'help': 'Best before date'},
                
                {'key': 'batch_number', 'label': 'Batch Number', 'type': 'text', 'required': False, 'order': 6,
                 'placeholder': 'Batch/Lot number'},
                
                {'key': 'country_of_origin', 'label': 'Country of Origin', 'type': 'text', 'required': True, 'order': 7,
                 'placeholder': 'e.g., India, USA'},
                
                {'key': 'usage_instructions', 'label': 'Usage Instructions', 'type': 'textarea', 'required': False, 'order': 8,
                 'placeholder': 'How to use this product'},
                
                {'key': 'safety_warning', 'label': 'Safety Warning', 'type': 'textarea', 'required': False, 'order': 9,
                 'placeholder': 'Any warnings or precautions'},
                
                {'key': 'dermatologically_tested', 'label': 'Dermatologically Tested', 'type': 'select', 'required': False, 'order': 10,
                 'options': 'Yes,No', 'help': 'Is the product dermatologically tested?'},
            ],
            
            # =============================
            # ELECTRONICS
            # =============================
            'Electronics': [
                {'key': 'model_number', 'label': 'Model Number', 'type': 'text', 'required': True, 'order': 1,
                 'placeholder': 'Model/SKU number'},
                
                {'key': 'warranty_period', 'label': 'Warranty Period', 'type': 'text', 'required': True, 'order': 2,
                 'placeholder': 'e.g., 1 year, 6 months'},
                
                {'key': 'power_requirement', 'label': 'Power Requirement', 'type': 'text', 'required': False, 'order': 3,
                 'placeholder': 'e.g., 220V, USB powered'},
                
                {'key': 'battery_type', 'label': 'Battery Type/Capacity', 'type': 'text', 'required': False, 'order': 4,
                 'placeholder': 'e.g., Li-ion 5000mAh, AA batteries'},
                
                {'key': 'ram_storage', 'label': 'RAM/Storage', 'type': 'text', 'required': False, 'order': 5,
                 'placeholder': 'e.g., 8GB RAM, 128GB Storage'},
                
                {'key': 'screen_size', 'label': 'Screen Size', 'type': 'text', 'required': False, 'order': 6,
                 'placeholder': 'e.g., 6.5 inches'},
                
                {'key': 'connectivity', 'label': 'Connectivity', 'type': 'text', 'required': False, 'order': 7,
                 'placeholder': 'e.g., WiFi, Bluetooth, USB'},
                
                {'key': 'inbox_contents', 'label': 'In-Box Contents', 'type': 'textarea', 'required': False, 'order': 8,
                 'placeholder': 'What comes in the box?'},
                
                {'key': 'return_policy', 'label': 'Return Policy', 'type': 'text', 'required': False, 'order': 9,
                 'placeholder': 'e.g., 7 days replacement'},
            ],
            
            # =============================
            # SPORTS
            # =============================
            'Sports': [
                {'key': 'sport_type', 'label': 'Sport Type', 'type': 'select', 'required': True, 'order': 1,
                 'options': 'Cricket,Football,Basketball,Tennis,Badminton,Gym,Yoga,Swimming,Other'},
                
                {'key': 'product_size', 'label': 'Size', 'type': 'text', 'required': False, 'order': 2,
                 'placeholder': 'e.g., Standard, Large'},
                
                {'key': 'material', 'label': 'Material', 'type': 'text', 'required': False, 'order': 3,
                 'placeholder': 'e.g., Leather, Synthetic'},
                
                {'key': 'sport_weight', 'label': 'Weight', 'type': 'text', 'required': False, 'order': 4,
                 'placeholder': 'Product weight'},
                
                {'key': 'skill_level', 'label': 'Skill Level', 'type': 'select', 'required': False, 'order': 5,
                 'options': 'Beginner,Intermediate,Professional,All Levels'},
                
                {'key': 'age_group', 'label': 'Age Group', 'type': 'select', 'required': False, 'order': 6,
                 'options': 'Kids,Teens,Adults,All Ages'},
                
                {'key': 'gender', 'label': 'Gender', 'type': 'select', 'required': False, 'order': 7,
                 'options': 'Men,Women,Unisex,Kids'},
            ],
            
            # =============================
            # FOODS & BEVERAGES
            # =============================
            # FOODS & BEVERAGES
            # =============================
            'Foods & Beverages': [
                {'key': 'fssai_license', 'label': 'FSSAI License Number', 'type': 'text', 'required': False, 'order': 1,
                 'placeholder': 'FSSAI registration number', 'help': 'Recommended for food products in India'},
                
                {'key': 'net_weight_volume', 'label': 'Net Weight/Volume', 'type': 'text', 'required': False, 'order': 2,
                 'placeholder': 'e.g., 500g, 1L, 250ml'},
                
                {'key': 'ingredients_list', 'label': 'Ingredients', 'type': 'textarea', 'required': False, 'order': 3,
                 'placeholder': 'List all ingredients'},
                
                {'key': 'nutritional_info', 'label': 'Nutritional Information', 'type': 'textarea', 'required': False, 'order': 4,
                 'placeholder': 'Calories, protein, fat, etc.'},
                
                {'key': 'manufacturing_date', 'label': 'Manufacturing Date', 'type': 'date', 'required': False, 'order': 5},
                
                {'key': 'expiry_date_food', 'label': 'Expiry/Best Before Date', 'type': 'date', 'required': False, 'order': 6},
                
                {'key': 'storage_instructions', 'label': 'Storage Instructions', 'type': 'textarea', 'required': False, 'order': 7,
                 'placeholder': 'How to store this product'},
                
                {'key': 'veg_nonveg', 'label': 'Veg/Non-Veg', 'type': 'select', 'required': False, 'order': 8,
                 'options': 'Vegetarian,Non-Vegetarian,Vegan,Eggitarian'},
                
                {'key': 'allergen_info', 'label': 'Allergen Information', 'type': 'textarea', 'required': False, 'order': 9,
                 'placeholder': 'Contains nuts, gluten, etc.'},
            ],
            
            # =============================
            # FURNITURE
            # =============================
            'Furniture': [
                {'key': 'furniture_material', 'label': 'Material', 'type': 'text', 'required': True, 'order': 1,
                 'placeholder': 'e.g., Wood, Metal, Fabric'},
                
                {'key': 'furniture_dimensions', 'label': 'Dimensions (L×W×H)', 'type': 'text', 'required': True, 'order': 2,
                 'placeholder': 'e.g., 120cm × 60cm × 75cm'},
                
                {'key': 'weight_capacity', 'label': 'Weight Capacity', 'type': 'text', 'required': False, 'order': 3,
                 'placeholder': 'e.g., 100kg'},
                
                {'key': 'assembly_required', 'label': 'Assembly Required', 'type': 'select', 'required': True, 'order': 4,
                 'options': 'Yes,No'},
                
                {'key': 'finish_type', 'label': 'Finish Type', 'type': 'text', 'required': False, 'order': 5,
                 'placeholder': 'e.g., Matte, Glossy, Polished'},
                
                {'key': 'room_type', 'label': 'Room Type', 'type': 'select', 'required': False, 'order': 6,
                 'options': 'Bedroom,Living Room,Dining Room,Office,Outdoor,Multi-purpose'},
                
                {'key': 'furniture_warranty', 'label': 'Warranty', 'type': 'text', 'required': False, 'order': 7,
                 'placeholder': 'e.g., 1 year manufacturing defects'},
            ],
            
            # =============================
            # HOME & KITCHEN
            # =============================
            'Home & Kitchen': [
                {'key': 'kitchen_material', 'label': 'Material', 'type': 'text', 'required': True, 'order': 1,
                 'placeholder': 'e.g., Stainless Steel, Glass, Plastic'},
                
                {'key': 'microwave_safe', 'label': 'Microwave Safe', 'type': 'select', 'required': False, 'order': 2,
                 'options': 'Yes,No'},
                
                {'key': 'dishwasher_safe', 'label': 'Dishwasher Safe', 'type': 'select', 'required': False, 'order': 3,
                 'options': 'Yes,No'},
                
                {'key': 'heat_resistant', 'label': 'Heat Resistant', 'type': 'select', 'required': False, 'order': 4,
                 'options': 'Yes,No'},
                
                {'key': 'set_count', 'label': 'Set Count', 'type': 'number', 'required': False, 'order': 5,
                 'placeholder': 'Number of pieces in set'},
                
                {'key': 'usage_type', 'label': 'Usage Type', 'type': 'text', 'required': False, 'order': 6,
                 'placeholder': 'e.g., Cookware, Tableware, Storage'},
            ],
            
            # =============================
            # AUTO ACCESSORIES
            # =============================
            'Auto Accessories': [
                {'key': 'vehicle_type', 'label': 'Vehicle Type', 'type': 'select', 'required': True, 'order': 1,
                 'options': 'Car,Bike,Both'},
                
                {'key': 'compatible_models', 'label': 'Compatible Models', 'type': 'textarea', 'required': False, 'order': 2,
                 'placeholder': 'List compatible vehicle models'},
                
                {'key': 'installation_type', 'label': 'Installation Type', 'type': 'select', 'required': False, 'order': 3,
                 'options': 'Professional Installation Required,DIY,Plug and Play'},
                
                {'key': 'power_source', 'label': 'Power Source', 'type': 'text', 'required': False, 'order': 4,
                 'placeholder': 'e.g., 12V, USB, Battery'},
                
                {'key': 'auto_warranty', 'label': 'Warranty', 'type': 'text', 'required': False, 'order': 5,
                 'placeholder': 'e.g., 6 months'},
                
                {'key': 'package_contents', 'label': 'Package Contents', 'type': 'textarea', 'required': False, 'order': 6,
                 'placeholder': 'What is included in the package?'},
            ],
            
            # =============================
            # TRAVEL
            # =============================
            'Travel': [
                {'key': 'capacity', 'label': 'Capacity (Liters)', 'type': 'number', 'required': False, 'order': 1,
                 'placeholder': 'e.g., 50'},
                
                {'key': 'number_of_wheels', 'label': 'Number of Wheels', 'type': 'select', 'required': False, 'order': 2,
                 'options': '0,2,4,8'},
                
                {'key': 'lock_type', 'label': 'Lock Type', 'type': 'select', 'required': False, 'order': 3,
                 'options': 'Combination Lock,Key Lock,TSA Lock,No Lock'},
                
                {'key': 'waterproof', 'label': 'Waterproof', 'type': 'select', 'required': False, 'order': 4,
                 'options': 'Yes,No,Water Resistant'},
                
                {'key': 'cabin_size_compatible', 'label': 'Cabin Size Compatible', 'type': 'select', 'required': False, 'order': 5,
                 'options': 'Yes,No'},
                
                {'key': 'travel_material', 'label': 'Material', 'type': 'text', 'required': False, 'order': 6,
                 'placeholder': 'e.g., Polycarbonate, Nylon'},
                
                {'key': 'travel_warranty', 'label': 'Warranty', 'type': 'text', 'required': False, 'order': 7,
                 'placeholder': 'e.g., 1 year'},
            ],
        }
        
        created_count = 0
        updated_count = 0
        
        for category_name, attributes in category_attributes.items():
            try:
                # Get or create category
                category, cat_created = Category.objects.get_or_create(
                    name=category_name
                )
                
                if cat_created:
                    self.stdout.write(self.style.SUCCESS(f'✓ Created category: {category_name}'))
                
                # Create attribute templates
                for attr_data in attributes:
                    template, created = CategoryAttributeTemplate.objects.update_or_create(
                        category=category,
                        attribute_key=attr_data['key'],
                        defaults={
                            'attribute_label': attr_data['label'],
                            'field_type': attr_data['type'],
                            'options': attr_data.get('options', ''),
                            'placeholder': attr_data.get('placeholder', ''),
                            'help_text': attr_data.get('help', ''),
                            'is_required': attr_data.get('required', False),
                            'order': attr_data['order'],
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ Error with {category_name}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Setup complete!\n'
            f'   Created: {created_count} attribute templates\n'
            f'   Updated: {updated_count} attribute templates'
        ))
