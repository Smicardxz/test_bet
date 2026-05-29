"""
Script de nettoyage automatique du codebase
Supprime les fichiers et dossiers obsolètes identifiés dans l'audit
"""

import os
import shutil
from pathlib import Path


def cleanup_codebase():
    """Nettoie le codebase en supprimant les fichiers obsolètes"""
    
    base_path = Path(__file__).parent / "app"
    
    print("🧹 NETTOYAGE DU CODEBASE")
    print("=" * 60)
    
    # Compteurs
    files_deleted = 0
    dirs_deleted = 0
    errors = 0
    
    # 1. Supprimer dossier engines/ entier
    print("\n📁 Étape 1 : Suppression dossier engines/")
    engines_path = base_path / "engines"
    if engines_path.exists():
        try:
            shutil.rmtree(engines_path)
            print(f"   ✅ Supprimé : {engines_path}")
            dirs_deleted += 1
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            errors += 1
    else:
        print(f"   ℹ️ Déjà supprimé : {engines_path}")
    
    # 2. Supprimer modèles dupliqués
    print("\n📄 Étape 2 : Suppression modèles dupliqués")
    models_to_delete = [
        "team.py",
        "match.py",
        "odds.py",
        "anomaly.py",
        "team_stats.py"
    ]
    
    models_path = base_path / "models"
    for model_file in models_to_delete:
        file_path = models_path / model_file
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"   ✅ Supprimé : {file_path}")
                files_deleted += 1
            except Exception as e:
                print(f"   ❌ Erreur : {e}")
                errors += 1
        else:
            print(f"   ℹ️ Déjà supprimé : {file_path}")
    
    # 3. Supprimer main_api.py
    print("\n📄 Étape 3 : Suppression point d'entrée dupliqué")
    main_api_path = base_path / "main_api.py"
    if main_api_path.exists():
        try:
            main_api_path.unlink()
            print(f"   ✅ Supprimé : {main_api_path}")
            files_deleted += 1
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            errors += 1
    else:
        print(f"   ℹ️ Déjà supprimé : {main_api_path}")
    
    # 4. Supprimer dossier ingestion/ s'il est vide
    print("\n📁 Étape 4 : Suppression dossier ingestion/")
    ingestion_path = base_path / "services" / "ingestion"
    if ingestion_path.exists():
        try:
            # Vérifier si vide ou contient seulement __init__.py
            contents = list(ingestion_path.iterdir())
            if not contents or (len(contents) == 1 and contents[0].name == "__init__.py"):
                shutil.rmtree(ingestion_path)
                print(f"   ✅ Supprimé : {ingestion_path}")
                dirs_deleted += 1
            else:
                print(f"   ⚠️ Dossier non vide, contient : {[f.name for f in contents]}")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            errors += 1
    else:
        print(f"   ℹ️ Déjà supprimé : {ingestion_path}")
    
    # 5. Supprimer core/database.py si existe (duplication avec db/)
    print("\n📄 Étape 5 : Suppression core/database.py (duplication)")
    core_db_path = base_path / "core" / "database.py"
    if core_db_path.exists():
        try:
            core_db_path.unlink()
            print(f"   ✅ Supprimé : {core_db_path}")
            files_deleted += 1
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            errors += 1
    else:
        print(f"   ℹ️ Déjà supprimé : {core_db_path}")
    
    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DU NETTOYAGE")
    print("=" * 60)
    print(f"✅ Fichiers supprimés : {files_deleted}")
    print(f"✅ Dossiers supprimés : {dirs_deleted}")
    print(f"❌ Erreurs : {errors}")
    print(f"📦 Total items supprimés : {files_deleted + dirs_deleted}")
    
    if errors == 0:
        print("\n✨ Nettoyage terminé avec succès !")
    else:
        print(f"\n⚠️ Nettoyage terminé avec {errors} erreur(s)")
    
    return files_deleted + dirs_deleted, errors


if __name__ == "__main__":
    print("\n⚠️ ATTENTION : Ce script va supprimer des fichiers !")
    print("Fichiers qui seront supprimés :")
    print("  - app/engines/ (dossier entier)")
    print("  - app/models/team.py")
    print("  - app/models/match.py")
    print("  - app/models/odds.py")
    print("  - app/models/anomaly.py")
    print("  - app/models/team_stats.py")
    print("  - app/main_api.py")
    print("  - app/services/ingestion/ (si vide)")
    print("  - app/core/database.py (si existe)")
    print()
    
    response = input("Continuer ? (oui/non) : ").strip().lower()
    
    if response in ["oui", "o", "yes", "y"]:
        total, errors = cleanup_codebase()
        
        if errors == 0:
            print("\n🎉 Le codebase est maintenant propre !")
            print("📝 Prochaine étape : Vérifier que tout fonctionne")
            print("   python -m app.main")
        else:
            print("\n⚠️ Vérifiez les erreurs ci-dessus")
    else:
        print("\n❌ Nettoyage annulé")
