from marshmallow import Schema, fields, ValidationError

class UpdateLayerSchema(Schema):
    project_id = fields.Int(required=True)
    file_id = fields.Int(required=True)
    layer_id = fields.Str(required=True)
    content = fields.Str(required=True)
    layer_type = fields.Str(required=True)

class BatchProcessSchema(Schema):
    files = fields.List(fields.Field(), required=True)

class UploadFileSchema(Schema):
    file = fields.Field(required=True)
    project_id = fields.Int(required=True) 