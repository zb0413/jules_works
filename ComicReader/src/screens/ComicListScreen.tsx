import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, Button, Alert, Platform, Image } from 'react-native'; // Added Image
import { pick, types } from '@react-native-documents/picker';
import RNFS from 'react-native-fs';
import { unzip } from 'react-native-zip-archive';
import { Buffer } from 'buffer'; // Required for base64 decoding if needed, or general buffer operations

// Ensure Buffer is globally available for libraries that might expect it (like some older zip libs or crypto)
if (typeof global.Buffer === 'undefined') {
  global.Buffer = Buffer;
}


export interface ComicListItem { // Exporting the interface
  id: string; // Should be a unique identifier, e.g., path to the comic directory
  title: string;
  coverImage?: string; // Path to local cover image (first page of the comic)
  pages: string[]; // Array of file URIs for comic pages
}

// Define navigation props if using React Navigation
// We'll get navigation prop from AppNavigator.tsx using NativeStackScreenProps
import { ComicListNavProps } from '../navigation/AppNavigator'; // Import navigation props type

// Remove the old onPressComic from props, navigation will be handled via navigation prop
// interface ComicListScreenProps {
//   onPressComic?: (comic: ComicListItem) => void;
// }

const COMICS_DIRECTORY = `${RNFS.DocumentDirectoryPath}/comics`;

// Update component to use navigation props
const ComicListScreen: React.FC<ComicListNavProps> = ({ navigation }) => {
  const [comics, setComics] = useState<ComicListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  // Function to create comics directory if it doesn't exist
  const ensureComicsDirExists = async () => {
    try {
      const exists = await RNFS.exists(COMICS_DIRECTORY);
      if (!exists) {
        await RNFS.mkdir(COMICS_DIRECTORY);
        console.log('Comics directory created at:', COMICS_DIRECTORY);
      }
    } catch (error) {
      console.error('Error creating comics directory:', error);
      Alert.alert('Error', 'Could not create storage for comics.');
    }
  };

  // Function to load comics from the filesystem
  const loadComicsFromStorage = useCallback(async () => {
    setIsLoading(true);
    await ensureComicsDirExists();
    try {
      const comicFolders = await RNFS.readDir(COMICS_DIRECTORY);
      const loadedComics: ComicListItem[] = [];

      for (const folder of comicFolders) {
        if (folder.isDirectory()) {
          const comicDirPath = folder.path;
          const files = await RNFS.readDir(comicDirPath);
          const imageFiles = files
            .filter(file => file.isFile() && /\.(jpe?g|png|gif|webp)$/i.test(file.name))
            .sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' })) // Natural sort
            .map(file => `file://${file.path}`); // Ensure file:// prefix for Image component

          if (imageFiles.length > 0) {
            loadedComics.push({
              id: comicDirPath, // Use directory path as ID
              title: folder.name, // Use folder name as title
              coverImage: imageFiles[0],
              pages: imageFiles,
            });
          }
        }
      }
      setComics(loadedComics);
    } catch (error) {
      console.error('Error loading comics from storage:', error);
      Alert.alert('Error', 'Could not load comics.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadComicsFromStorage();
  }, [loadComicsFromStorage]);


  const handleImportComic = async () => {
    setIsLoading(true);
    await ensureComicsDirExists();
    try {
      const results = await pick({
        type: [types.zip],
        mode: 'open', // 'open' for single file, 'import' might also work
        // copyTo: 'cachesDirectory', // For temporary access, then we'll move it
      });

      if (results && results.length > 0) {
        const pickedFile = results[0];
        const sourcePath = pickedFile.uri;
        // For Android, if URI is content://, we need to copy it to a readable path first
        let actualSourcePath = Platform.OS === 'android' && sourcePath.startsWith('content://')
          ? `${RNFS.CachesDirectoryPath}/${pickedFile.name || 'temp.zip'}`
          : sourcePath.replace('file://', '');

        if (Platform.OS === 'android' && sourcePath.startsWith('content://')) {
            await RNFS.copyFile(sourcePath, actualSourcePath);
        }


        // Sanitize filename to create a valid directory name
        const comicName = (pickedFile.name || `comic_${Date.now()}`).replace(/\.zip$/i, '').replace(/[^a-zA-Z0-9_.-]/g, '_');
        const targetPath = `${COMICS_DIRECTORY}/${comicName}`;

        const targetExists = await RNFS.exists(targetPath);
        if (targetExists) {
          Alert.alert('Comic Exists', `A comic with name "${comicName}" already exists. Please rename the ZIP or delete the existing one.`);
          setIsLoading(false);
          // Clean up copied file if it was created
          if (Platform.OS === 'android' && sourcePath.startsWith('content://') && actualSourcePath.includes(RNFS.CachesDirectoryPath)) {
            await RNFS.unlink(actualSourcePath);
          }
          return;
        }
        await RNFS.mkdir(targetPath); // Create directory for the comic

        console.log(`Unzipping from ${actualSourcePath} to ${targetPath}`);
        await unzip(actualSourcePath, targetPath);
        console.log('Unzip successful');

        // Clean up the temporary copied file on Android if it exists in cache
        if (Platform.OS === 'android' && sourcePath.startsWith('content://') && actualSourcePath.includes(RNFS.CachesDirectoryPath)) {
            await RNFS.unlink(actualSourcePath);
        }
        // Also try to clean up original if it was a cache copy from document picker (iOS might do this)
        // This is often named with `RNFS_document_picker_` prefix on iOS if copied by the picker itself.
        if (pickedFile.fileCopyUri) {
             try {
                await RNFS.unlink(pickedFile.fileCopyUri.replace('file://', ''));
             } catch (unlinkError) {
                console.warn('Could not clean up picker temp file:', unlinkError);
             }
        }

        Alert.alert('Import Successful', `Comic "${comicName}" imported.`);
        loadComicsFromStorage(); // Refresh the list
      }
    } catch (err: any) {
      // Check for user cancellation codes or messages
      if (err.code === 'DOCUMENT_PICKER_CANCELED' || (err.message && err.message.toLowerCase().includes('cancelled'))) {
        console.log('User cancelled the document picker.');
      } else {
        console.error('Import error:', err);
        Alert.alert('Import Error', `Failed to import comic: ${err.message || 'Unknown error'}`);
      }
    } finally {
      setIsLoading(false);
    }
  };


  const renderItem = ({ item }: { item: ComicListItem }) => (
    <TouchableOpacity
      style={styles.itemContainer}
      onPress={() => navigation.navigate('ComicView', { comic: item })} // Navigate to ComicView with comic data
    >
      <View style={styles.coverImageContainer}>
        {item.coverImage ? (
          <Image source={{ uri: item.coverImage }} style={styles.coverImage} resizeMode="cover" />
        ) : (
          <View style={styles.coverImagePlaceholder} />
        )}
      </View>
      <Text style={styles.itemTitle} numberOfLines={2} ellipsizeMode="tail">{item.title}</Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>My Comics</Text>
        <Button title={isLoading ? "Importing..." : "Import ZIP"} onPress={handleImportComic} disabled={isLoading} />
      </View>
      {isLoading && comics.length === 0 && <Text style={styles.loadingText}>Loading comics...</Text>}
      <FlatList
        data={comics}
        renderItem={renderItem}
        keyExtractor={(item) => item.id}
        ListEmptyComponent={!isLoading && comics.length === 0 ? <Text style={styles.emptyListText}>No comics imported yet. Tap 'Import ZIP' to add some!</Text> : null}
        contentContainerStyle={comics.length === 0 && !isLoading ? styles.emptyListContainer : null}
        onRefresh={loadComicsFromStorage} // Pull to refresh
        refreshing={isLoading}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 15,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#cccccc',
    backgroundColor: '#f9f9f9',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  itemContainer: {
    flexDirection: 'row',
    padding: 10,
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#cccccc',
  },
  coverImageContainer: {
    width: 60,
    height: 90,
    marginRight: 10,
    justifyContent: 'center',
    alignItems: 'center',
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#e0e0e0',
  },
  coverImage: {
    width: '100%',
    height: '100%',
  },
  coverImagePlaceholder: { // Now used as a fallback within coverImageContainer
    width: '100%',
    height: '100%',
    backgroundColor: '#e0e0e0',
  },
  itemTitle: {
    fontSize: 16,
    flex: 1, // Allow title to take remaining space
  },
  loadingText: {
    textAlign: 'center',
    marginTop: 20,
    fontSize: 16,
  },
  emptyListText: {
    textAlign: 'center',
    marginTop: 50,
    fontSize: 16,
  },
  emptyListContainer: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
  }
});

export default ComicListScreen;
