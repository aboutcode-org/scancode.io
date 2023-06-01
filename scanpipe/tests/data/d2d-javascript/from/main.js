// Set the possible characters for the password
const charSet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890!@#$%^&*()_-+=";

// Function to generate a random password
function generatePassword(length) {
  let password = "";
  for (let i = 0; i < length; i++) {
    // Choose a random character from the character set
    const randomIndex = Math.floor(Math.random() * charSet.length);
    const randomChar = charSet[randomIndex];
    // Add the random character to the password string
    password += randomChar;
  }
  return password;
}

// Get the password length from the user
const passwordLength = parseInt(prompt("Enter the desired length of your password:"));

// Generate the password and display it to the user
const password = generatePassword(passwordLength);
alert(`Your random password is: ${password}`);
