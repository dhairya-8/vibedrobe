from django.shortcuts import render

def homepage(request):
   return render(request, 'homepage.html')

def shop(request):
   return render(request, 'shop.html')

def product_detail(request):
   return render(request, 'product_detail.html')

def cart(request):
   return render(request,'cart.html')

def user_login(request):
   return render(request, 'user_login.html')

def register(request):
   return render(request, 'register.html')

def contactus(request):
   return render(request, 'contactus.html')

def aboutus(request):
   return render(request, 'aboutus.html')

def orderconfirm(request):
   return render(request, 'orderconfirm.html')

def checkout(request):
   return render(request, 'checkout.html')

def forgotpassword(request):
   return render(request, 'forgotpassword.html')