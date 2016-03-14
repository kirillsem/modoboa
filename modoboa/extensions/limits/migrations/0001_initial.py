# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from modoboa.lib.compat import user_model_name


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'LimitsPool'
        db.create_table('limits_limitspool', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm[user_model_name], unique=True)),
        ))
        db.send_create_signal('limits', ['LimitsPool'])

        # Adding model 'Limit'
        db.create_table('limits_limit', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('curvalue', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('maxvalue', self.gf('django.db.models.fields.IntegerField')(default=-2)),
            ('pool', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['limits.LimitsPool'])),
        ))
        db.send_create_signal('limits', ['Limit'])

        # Adding unique constraint on 'Limit', fields ['name', 'pool']
        db.create_unique('limits_limit', ['name', 'pool_id'])


    def backwards(self, orm):
        
        # Removing unique constraint on 'Limit', fields ['name', 'pool']
        db.delete_unique('limits_limit', ['name', 'pool_id'])

        # Deleting model 'LimitsPool'
        db.delete_table('limits_limitspool')

        # Deleting model 'Limit'
        db.delete_table('limits_limit')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        user_model_name: {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'limits.limit': {
            'Meta': {'unique_together': "(('name', 'pool'),)", 'object_name': 'Limit'},
            'curvalue': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'maxvalue': ('django.db.models.fields.IntegerField', [], {'default': '-2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'pool': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['limits.LimitsPool']"})
        },
        'limits.limitspool': {
            'Meta': {'object_name': 'LimitsPool'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['%s']" % user_model_name, 'unique': 'True'})
        }
    }

    complete_apps = ['limits']
