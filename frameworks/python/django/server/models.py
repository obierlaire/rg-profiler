"""
Database models for the Django version of RG Profiler
"""
from django.db import models


class World(models.Model):
    """World model for DB benchmark tests"""
    id = models.IntegerField(primary_key=True)
    randomnumber = models.IntegerField()
    
    class Meta:
        db_table = 'world'


class Fortune(models.Model):
    """Fortune model for template benchmarks"""
    id = models.IntegerField(primary_key=True)
    message = models.TextField()
    
    class Meta:
        db_table = 'fortune'


class User(models.Model):
    """User model for session tests"""
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=100)
    email = models.EmailField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'


class Session(models.Model):
    """Custom Session model for session tests"""
    id = models.CharField(max_length=100, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'sessions'


class ComplexData(models.Model):
    """Complex data model for serialization tests"""
    name = models.CharField(max_length=100)
    data = models.JSONField()
    tags = models.JSONField()  # Store as JSON array
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'complex_data'