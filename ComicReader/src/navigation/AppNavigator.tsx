import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator, NativeStackScreenProps } from '@react-navigation/native-stack';

import ComicListScreen from '../screens/ComicListScreen';
import ComicViewScreen from '../screens/ComicViewScreen';
import { ComicListItem } from '../screens/ComicListScreen'; // Assuming ComicListItem is exported

// Define the types for the navigation stack parameters
export type RootStackParamList = {
  ComicList: undefined; // No parameters expected for ComicListScreen
  ComicView: { comic: ComicListItem }; // ComicViewScreen expects a comic object
};

// Props for ComicListScreen - useful if you need navigation prop directly in ComicListScreen
export type ComicListNavProps = NativeStackScreenProps<RootStackParamList, 'ComicList'>;

// Props for ComicViewScreen - to get route params
export type ComicViewNavProps = NativeStackScreenProps<RootStackParamList, 'ComicView'>;


const Stack = createNativeStackNavigator<RootStackParamList>();

const AppNavigator: React.FC = () => {
  return (
    <NavigationContainer>
      <Stack.Navigator initialRouteName="ComicList">
        <Stack.Screen
          name="ComicList"
          component={ComicListScreen}
          options={{ title: 'My Comics' }} // Set a default title for the list screen
        />
        <Stack.Screen
          name="ComicView"
          component={ComicViewScreen}
          options={({ route }) => ({
            title: route.params.comic.title, // Set title from comic data
            headerBackTitleVisible: false, // Optional: hide back button text on iOS
          })}
        />
      </Stack.Navigator>
    </NavigationContainer>
  );
};

export default AppNavigator;
