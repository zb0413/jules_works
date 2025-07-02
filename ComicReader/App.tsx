/**
 * Sample React Native App
 * https://github.com/facebook/react-native
 *
 * @format
 */

import React from 'react';
// SafeAreaView, StatusBar, StyleSheet, useColorScheme can be removed if not used globally here
// For now, we'll keep StatusBar for global style and wrap AppNavigator.
import { StatusBar, useColorScheme, StyleSheet, View } from 'react-native';
import AppNavigator from './src/navigation/AppNavigator'; // Import the AppNavigator

// It's good practice for gesture handler to be at the very top
// import 'react-native-gesture-handler'; // Already handled by react-navigation if it's a dep

function App(): React.JSX.Element {
  const isDarkMode = useColorScheme() === 'dark';

  // The NavigationContainer will provide its own background,
  // so we might not need SafeAreaView here unless for specific global layout.
  // Let's simplify and let AppNavigator handle the screen views.
  // StatusBar can still be useful.

  const appStyles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: isDarkMode ? '#000000' : '#FFFFFF', // Default background for the app
    },
  });

  return (
    <View style={appStyles.container}>
      <StatusBar
        barStyle={isDarkMode ? 'light-content' : 'dark-content'}
        backgroundColor={appStyles.container.backgroundColor} // Match status bar bg to app bg
      />
      <AppNavigator />
    </View>
  );
}

export default App;
