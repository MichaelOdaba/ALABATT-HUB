from django.db import migrations, models


def populate_available_quantity(apps, schema_editor):
    Equipment = apps.get_model('accounts', 'Equipment')
    EquipmentLoan = apps.get_model('accounts', 'EquipmentLoan')
    database = schema_editor.connection.alias

    stock_rows = []
    invalid_equipment_ids = []
    for equipment in Equipment.objects.using(database).all().iterator():
        loaned_quantity = sum(
            EquipmentLoan.objects.using(database)
            .filter(
                equipment_id=equipment.pk,
                status__in=['active', 'overdue'],
            )
            .values_list('quantity', flat=True)
        )
        available_quantity = equipment.quantity - loaned_quantity
        if available_quantity < 0:
            invalid_equipment_ids.append(equipment.pk)
        else:
            stock_rows.append((equipment.pk, available_quantity))

    if invalid_equipment_ids:
        raise RuntimeError(
            'Existing active equipment loans exceed total stock for equipment IDs: '
            f'{invalid_equipment_ids}. Resolve these records before migrating.'
        )

    for equipment_id, available_quantity in stock_rows:
        Equipment.objects.using(database).filter(pk=equipment_id).update(
            available_quantity=available_quantity
        )


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_booking_is_event_equipmentloan_deposit_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='equipment',
            name='available_quantity',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.RunPython(
            populate_available_quantity,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='equipment',
            name='available_quantity',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name='equipmentloan',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending deposit'),
                    ('active', 'Active'),
                    ('returned', 'Returned'),
                    ('overdue', 'Overdue'),
                    ('lost', 'Lost'),
                    ('cancelled', 'Cancelled'),
                ],
                default='active',
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name='equipment',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    available_quantity__lte=models.F('quantity')
                ),
                name='equipment_available_not_above_total',
            ),
        ),
    ]
