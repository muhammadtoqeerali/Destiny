"""Explicit synthetic demo schema. These are NOT actual HUNT Databank codes."""

NUMERIC_FEATURES = [
    'age', 'bmi', 'grip_strength_kg', 'gait_speed_ms', 'sppb_score',
    'moca_score', 'weight_loss', 'exhaustion', 'medication_count',
    'oral_health_problem', 'activity_minutes_day', 'previous_fall',
    'comorbidity_count',
]
CATEGORICAL_FEATURES = ['sex']
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = 'fall_within_12m'
ID_COL = 'patient_id'
PROVENANCE_COL = 'data_origin'

FEATURE_LABELS = {
    'age': 'Age', 'bmi': 'Body mass index',
    'grip_strength_kg': 'Grip strength', 'gait_speed_ms': 'Walking speed',
    'sppb_score': 'Physical function (SPPB)', 'moca_score': 'Cognition (MoCA)',
    'weight_loss': 'Recent weight loss', 'exhaustion': 'Exhaustion',
    'medication_count': 'Medication count', 'oral_health_problem': 'Oral health problem',
    'activity_minutes_day': 'Daily activity', 'previous_fall': 'Previous fall',
    'comorbidity_count': 'Comorbidity count', 'sex': 'Sex'
}
FEATURE_UNITS = {
    'age': 'years', 'bmi': 'kg/m²', 'grip_strength_kg': 'kg',
    'gait_speed_ms': 'm/s', 'sppb_score': '/12', 'moca_score': '/30',
    'activity_minutes_day': 'min/day',
}
