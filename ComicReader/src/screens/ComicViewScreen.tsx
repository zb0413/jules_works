import React, { useState, useEffect, useLayoutEffect } from 'react';
import { View, Text, Image, StyleSheet, Dimensions, TouchableOpacity, FlatList, ActivityIndicator } from 'react-native';
import { ComicViewNavProps } from '../navigation/AppNavigator'; // Import navigation props type

// Placeholder for actual image URIs - will be replaced by route.params.comic.pages
// const MOCK_PAGE_URIS = [
//   'https://via.placeholder.com/400x600.png?text=Page+1',
//   'https://via.placeholder.com/400x600.png?text=Page+2',
//   'https://via.placeholder.com/400x600.png?text=Page+3',
// ];

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

const ComicViewScreen: React.FC<ComicViewNavProps> = ({ route, navigation }) => {
  const { comic } = route.params; // Get the comic object from navigation params

  const [pages, setPages] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const flatListRef = React.useRef<FlatList<string>>(null);

  // Set the header title dynamically - useLayoutEffect runs before useEffect
  // useLayoutEffect(() => {
  //   navigation.setOptions({ title: comic.title || 'Comic Viewer' });
  // }, [navigation, comic.title]);
  // Header title is now set in AppNavigator options for this screen

  useEffect(() => {
    if (comic && comic.pages && comic.pages.length > 0) {
      setPages(comic.pages);
      setCurrentPage(0); // Reset to first page when comic changes
      // Scroll to the first page if the list was already rendered for a previous comic
      flatListRef.current?.scrollToOffset({ animated: false, offset: 0 });
    } else {
      // Handle case where comic or pages are not available (e.g., show an error or placeholder)
      setPages([]);
      console.warn('Comic data or pages not found in route params.');
    }
    setIsLoading(false);
  }, [comic]);

  const renderPage = ({ item, index }: { item: string, index: number }) => {
    return (
      <View style={styles.pageContainer}>
        <Image source={{ uri: item }} style={styles.pageImage} resizeMode="contain" />
      </View>
    );
  };

  const goToNextPage = () => {
    if (currentPage < pages.length - 1) {
      flatListRef.current?.scrollToIndex({ index: currentPage + 1 });
      // setCurrentPage(currentPage + 1); // Handled by onMomentumScrollEnd
    }
  };

  const goToPreviousPage = () => {
    if (currentPage > 0) {
      flatListRef.current?.scrollToIndex({ index: currentPage - 1 });
      // setCurrentPage(currentPage - 1); // Handled by onMomentumScrollEnd
    }
  };

  // Update current page based on scroll position
  const handleScroll = (event: any) => {
    const newPage = Math.round(event.nativeEvent.contentOffset.x / screenWidth);
    if (newPage !== currentPage) {
      setCurrentPage(newPage);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" />
        <Text>Loading comic...</Text>
      </View>
    );
  }

  if (pages.length === 0) {
    return (
      <View style={styles.loadingContainer}>
        <Text>No pages found for this comic.</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        ref={flatListRef}
        data={pages}
        renderItem={renderPage}
        keyExtractor={(item, index) => `${comic.id}_page_${index}`} // Ensure unique keys if comic IDs can be similar to page content
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={handleScroll}
        initialNumToRender={1} // Optimization: render 1 page initially
        windowSize={3} // Optimization: render fewer pages outside viewport
        maxToRenderPerBatch={1} // Optimization
        getItemLayout={(data, index) => (
          { length: screenWidth, offset: screenWidth * index, index }
        )}
        // onViewableItemsChanged={onViewableItemsChangedRef.current}
        // viewabilityConfig={viewabilityConfigRef.current}
      />
      {pages.length > 1 && ( // Only show controls if there's more than one page
        <View style={styles.navigationControls}>
          <TouchableOpacity onPress={goToPreviousPage} disabled={currentPage === 0} style={styles.navButton}>
            <Text style={styles.navButtonText}>Previous</Text>
          </TouchableOpacity>
          <Text style={styles.pageIndicator}>Page {currentPage + 1} of {pages.length}</Text>
          <TouchableOpacity onPress={goToNextPage} disabled={currentPage >= pages.length - 1} style={styles.navButton}>
            <Text style={styles.navButtonText}>Next</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#000', // Match theme
  },
  pageContainer: {
    width: screenWidth,
    height: screenHeight, // Adjust if you have headers/footers
    justifyContent: 'center',
    alignItems: 'center',
  },
  pageImage: {
    width: screenWidth,
    height: '100%', // Or screenHeight - some_padding_for_controls
  },
  navigationControls: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'center',
    paddingVertical: 10,
    backgroundColor: 'rgba(50, 50, 50, 0.8)',
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
  },
  navButton: {
    padding: 10,
  },
  pageIndicator: {
    color: '#fff',
    fontSize: 16,
  },
});

export default ComicViewScreen;
