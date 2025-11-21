from __future__ import annotations

from marshmallow import Schema, fields, ValidationError, validates


class CityQuerySchema(Schema):
    city = fields.String(required=True, allow_none=False)

    @validates("city")
    def _validate_city(self, value: str, **kwargs):
        if not value.strip():
            raise ValidationError("city_required")


class DatasetHistoryQuerySchema(Schema):
    city = fields.String(load_default=None)
    limit = fields.Integer(load_default=100)

    @validates("limit")
    def _validate_limit(self, value: int, **kwargs):
        if value <= 0 or value > 500:
            raise ValidationError("limit_range")


class TrainAllQuerySchema(Schema):
    workers = fields.Integer(load_default=2)

    @validates("workers")
    def _validate_workers(self, value: int, **kwargs):
        if value < 1 or value > 8:
            raise ValidationError("workers_range")


class OptionalCitySchema(Schema):
    city = fields.String(load_default=None)
